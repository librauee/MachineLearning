using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Text;
using System.Windows.Forms;

using System.IO.Ports;
using System.Threading;
using System.Diagnostics;//Debug

namespace UARTDrawingCurve
{
    public partial class DrawingCurveForm : Form
    {
        UARTComSet ComObj = new UARTComSet();
        RealTimeImageMaker rti;
        Graphics Gph1;

        private const int ReadByteSize = 9;//设置读入的字节数
        private const int OriginX = 60;//原点坐标所在的X点位置
        int[] OriginScaleValue = new int[25];//X轴坐标刻度数量
        Queue<byte[]> RcvQueue = new Queue<byte[]>();//接收字节数据队列
        Queue<int> ConvertToIntQueue = new Queue<int>();//转换为int类型的队列

        Queue<int> tempIntQueue = new Queue<int>();
        Random rm = new Random();

        private bool IsLoop = true;
        private int CountTimer = 0;//统计循环时间，作为X轴坐标值
        private delegate void DisplayData(string StrDisplay);//防止跨线程访问异常
  //      private DisplayData DisplayDataDlg;
        private delegate void CoordinatesSet();//坐标轴设定
        private CoordinatesSet CoordinatesSetDlg;

        Thread DataDealThread;//接收字节处理线程

        public DrawingCurveForm()
        {
            InitializeComponent();
        }

        private void DrawingCurveForm_Load(object sender, EventArgs e)
        {
            #region 串口设置区载入值

            PortNameBox.Items.AddRange(new object[] { "COM1", "COM2","COM3","COM4" });//串口号
            string[] strcom = SerialPort.GetPortNames();
            if (strcom == null || strcom.Length == 0)
                MessageBox.Show("未检测到可通信串口,请先插入通信设备！", "Warning");
            //扫描串口项目
            foreach (string s in System.IO.Ports.SerialPort.GetPortNames())
            {//获取有多少个COM口
                if (s != "COM1")
                    PortNameBox.Items.Add(s);
            }
            PortNameBox.SelectedIndex = PortNameBox.Items.Count - 1;

            BaudRateBox.Items.AddRange(new object[] {"115200","38400","19200",
            "9600","4800","2400","1200"});//波特率
            BaudRateBox.SelectedIndex = 0;

            StopBitsBox.Items.AddRange(new object[] { "None", "One", "Two", "OnePointFive" });//停止位
            StopBitsBox.SelectedIndex = 1;

            DataBitsBox.Items.AddRange(new object[] { "6", "7", "8" });//数据位
            DataBitsBox.SelectedIndex = DataBitsBox.Items.Count - 1;

            ParityBitsBox.Items.AddRange(new object[] { "None", "Odd", "Even" });//停止位
            ParityBitsBox.SelectedIndex = 0;

            #endregion

            CoordinatesSetDlg = new CoordinatesSet(CoordinatesSetNethod);

            Gph1 = GraphicPanel.CreateGraphics();//将GraphicPanel作为画板
        }

        /// <summary>
        /// 委托调用函数设定初始坐标轴
        /// </summary>
        private void CoordinatesSetNethod()
        {
            Point OriginPoint = new Point(OriginX, GraphicPanel.Height - 40);
            Gph1.Transform = new Matrix(1, 0, 0, -1, OriginPoint.X, OriginPoint.Y);
            OriginCoordClass.DrawCoord(Gph1, OriginPoint, GraphicPanel.Width, GraphicPanel.Height);
            Point TargetPoint = new Point(GraphicPanel.Width, GraphicPanel.Height);
            OriginCoordClass.SetScale(Gph1, OriginPoint, TargetPoint, ref OriginScaleValue);
            Gph1.Transform = new Matrix(1, 0, 0, -1, OriginPoint.X, OriginPoint.Y);
        }

        #region 串口号改变
        private void PortNameBox_TextUpdate(object sender, EventArgs e)
        {
            ComObj.PortNameValue = PortNameBox.Text.Replace(" ", "");
        }

        private void PortNameBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            ComObj.PortNameValue = PortNameBox.Text;
        }
        #endregion

        #region 波特率改变
        private void BaudRateBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            ComObj.BaudRateValue = BaudRateBox.Text;
        }

        private void BaudRateBox_TextUpdate(object sender, EventArgs e)
        {
            ComObj.BaudRateValue = BaudRateBox.Text.Replace(" ", "");
        }
        #endregion

        #region 停止位改变
        private void StopBitsBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            ComObj.StopBitsValue = StopBitsBox.Text;
        }

        private void StopBitsBox_TextUpdate(object sender, EventArgs e)
        {
            ComObj.StopBitsValue = StopBitsBox.Text.Replace(" ", "");
        }
        #endregion

        #region 数据位改变
        private void DataBitsBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            ComObj.DataBitsValue = DataBitsBox.Text;
        }

        private void DataBitsBox_TextUpdate(object sender, EventArgs e)
        {
            ComObj.DataBitsValue = DataBitsBox.Text.Replace(" ", "");
        }
        #endregion

        #region 校验位改变
        private void ParityBitsBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            ComObj.ParityBitsValue = ParityBitsBox.Text;
        }

        private void ParityBitsBox_TextUpdate(object sender, EventArgs e)
        {
            ComObj.ParityBitsValue = ParityBitsBox.Text.Replace(" ", "");
        }
        #endregion

        /// <summary>
        /// 打开串口
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void OpenComBtn01_Click(object sender, EventArgs e)
        {
            try
            {
                ComObj.OpenCom();
                ComStatuesLable01.Text = "串口打开";
                ComObj.ComValue.DiscardInBuffer();
                RcvQueue.Clear();
                ConvertToIntQueue.Clear();

                #region 接收处理线程
                DataDealThread = new Thread(DataDealMethod);
                IsLoop = true;
                DataDealThread.Start();
                ComObj.ComValue.DataReceived += new SerialDataReceivedEventHandler(serialPort_DataReceived);
                #endregion

                #region 绘制实时动态图
                CountTimer = 0;
                rti = new RealTimeImageMaker(GraphicPanel.Width, GraphicPanel.Height, Color.Black);
                this.timer1.Enabled = true;
                this.timer1.Interval = 1000;
                this.timer1.Tick += new System.EventHandler(this.timer1_Tick);

                this.timer1.Start();
                #endregion
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "OpenWarning");
            }
        }       

        /// <summary>
        /// 接收数据
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void serialPort_DataReceived(object sender, SerialDataReceivedEventArgs e) 
        {
            try
            {
                int ReadCount = ComObj.ComValue.BytesToRead;
                if (ReadCount >= ReadByteSize)
                {
                    Byte[] UARTReceivedData = new Byte[ReadByteSize];
                    ComObj.ComValue.Read(UARTReceivedData, 0, UARTReceivedData.Length);         //读取数据
                    RcvQueue.Enqueue(UARTReceivedData);
                }
            }
            catch (System.Exception ex)
            {
                ComObj.ComValue.DiscardInBuffer();
                MessageBox.Show(ex.Message, "ReceiveWarning");
            }
        }

        /// <summary>
        /// 解析接收到的数据
        /// </summary>
        private void DataDealMethod()
        {
            while (IsLoop)
            {
              //  string StrLenTwoRcv = null;//接收到的字符串，十六进制长度为2
              //  string StrLenOneRcv = null;//接收到的字符串，十六进制长度为1
                try
                {
                    if (RcvQueue.Count >= 1)
                    {
                        byte[] ReceiveDataDeal = RcvQueue.Dequeue();

                   //     DisplayDataDlg = new DisplayData(DisplayMethod);

                  /*    ConvertClass.ConvertByteToHexString(ReceiveDataDeal, ref StrLenTwoRcv,ref StrLenOneRcv);
                        
                        this.BeginInvoke(DisplayDataDlg, StrLenTwoRcv);
                        this.BeginInvoke(DisplayDataDlg, StrLenOneRcv);*/

                        DecomposeClass DecomposeObj = new DecomposeClass();
                        DecomposeObj.ConvertToInt(ReceiveDataDeal, ref ConvertToIntQueue);
                     /*   while (ConvertToIntQueue.Count > 0)
                        {
                            this.BeginInvoke(DisplayDataDlg, ConvertToIntQueue.Dequeue().ToString());
                        }*/
                    }
                    else Thread.Sleep(1);
                }
                catch (Exception ex)
                {
                    MessageBox.Show(ex.Message, "DataDealWarning");
                    return;
                }
            }
        }

        /// <summary>
        /// 显示接收数据
        /// </summary>
        /// <param name="strDisplay">待显示的字符串</param>
        private void DisplayMethod(string strDisplay)
        {
            RcvDataText01.Text += strDisplay + "\r\n";
        }

        /// <summary>
        /// 关闭串口,同时关闭线程
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void CloseComBtn01_Click(object sender, EventArgs e)
        {
            try
            {
                ComObj.CloseCom();
                ComStatuesLable01.Text = "串口关闭";
                IsLoop = false;
                if (DataDealThread != null && DataDealThread.IsAlive)  //时刻关闭线程
                {
                    DataDealThread.Abort();
                }
                if (this.timer1.Enabled)
                {
                    this.timer1.Enabled = false;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "CloseWarning");
            }
        }

        /// <summary>
        /// 滑动条随接收数据变化
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void RcvDataText01_TextChanged(object sender, EventArgs e)
        {
            RcvDataText01.SelectionStart = RcvDataText01.Text.Length;
            RcvDataText01.ScrollToCaret();
        }

        /// <summary>
        /// 清空接收区
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void ClearTextBtn01_Click(object sender, EventArgs e)
        {
            RcvDataText01.Text = null;
            Gph1.Clear(Color.Black);
            CoordinatesSetDlg();
        }

        /// <summary>
        /// Paint触发时间
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void GraphicPanel_Paint(object sender, PaintEventArgs e)
        {
            CoordinatesSetDlg();
        }

        /// <summary>
        /// 调用绘图函数
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void timer1_Tick(object sender, EventArgs e)
        {
            tempIntQueue.Enqueue(rm.Next(0, 1024));
            PointF ReadPointValue = new PointF(0, 0);
            CountTimer++;
            float XTimerValue = (CountTimer * this.timer1.Interval) / 1000;
            float YVolValue = (tempIntQueue.Dequeue() * 30) / 100;
            ReadPointValue.Y = YVolValue;
            if ((int)XTimerValue < 25)
            {
                ReadPointValue.X = XTimerValue * 20;
                rti.GetCurrentCurve(Gph1, ReadPointValue);
            }
            else
            {
                int XMax = OriginScaleValue[OriginScaleValue.Length - 1] + 1;
                ReadPointValue.X = (XTimerValue - XMax + 24) * 20;
                Image image = rti.GetDynamicCurve(ReadPointValue, ref OriginScaleValue, XMax);
                Graphics Gph2 = GraphicPanel.CreateGraphics();
                Gph2.Clear(Color.Black);
                Gph2.DrawImage(image, 0, 0);
                Gph2.Dispose();
            }
        }

        /// <summary>
        /// 退出界面前需关闭相关线程
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void DrawingCurveForm_FormClosing(object sender, FormClosingEventArgs e)
        {
            try
            {
                ComObj.CloseCom();
                IsLoop = false;
                if (DataDealThread != null && DataDealThread.IsAlive)  //时刻关闭线程
                {
                    DataDealThread.Abort();
                }
                if (this.timer1.Enabled)
                {
                    this.timer1.Enabled = false;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "FormClosingWarning");
            }
        }
    }
}
