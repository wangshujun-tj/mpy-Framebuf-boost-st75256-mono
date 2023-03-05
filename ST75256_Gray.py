# MicroPython ST75256 Gray LCD driver, I2C and SPI interfaces

from micropython import const
import framebuf

class ST75256(framebuf.FrameBuffer):
    def __init__(self, width, height, rot=0):
        self.width = width
        self.height = height
        self.rot=rot 
        self.buffer = bytearray(self.height * self.width//4)
        if self.rot==0 or self.rot==2:
            super().__init__(self.buffer, self.width, self.height, framebuf.GS2_VLSB, self.width)
        else:
            super().__init__(self.buffer, self.height, self.width, framebuf.GS2_HLSB, self.height)
        self.init_display()

    def init_display(self):
        
        cmd_list=[
            [0x30,],#扩展指令1
            [0x94,],#退出睡眠模式
            [0x31,],#扩展指令2
            [0xD7,0X9F],#禁止自动读
            [0x32,0x00,0x01,0x03],#偏压比设置
            [0xF2,0x1e,0x28,0x32],#温度范围设置
            [0x20,0x01,0x03,0x05,0x07,0x09,0x0b,0x0d,0x10,0x11,
             0x13,0x15,0x17,0x19,0x1b,0x1d,0x1f],#灰度级控制
            [0x30,],#扩展指令1
            [0xCA,0X00,0X9F,0X20],#显示控制，cl，占空比，帧周期
            [0xF0,0X11],#灰度显示
            [0x81,0x0a,0x04],#设置对比度
            [0x20,0x0B] ]#电源控制

        for cmd in cmd_list:
            self.write_cmd(cmd)
        if self.rot==0:
            self.write_cmd([0x08,])#数据格式选择，d0到d7的排列方向0x08/0x0c
            self.write_cmd([0xBC,0X03])#扫描方向控制
        elif self.rot==1:
            self.write_cmd([0x08,])#数据格式选择，d0到d7的排列方向0x08/0x0c
            self.write_cmd([0xBC,0X05])#扫描方向控制
        elif self.rot==2:
            self.write_cmd([0x0C,])#数据格式选择，d0到d7的排列方向0x08/0x0c
            self.write_cmd([0xBC,0X00])#扫描方向控制
        else :
            self.write_cmd([0x0c,])#数据格式选择，d0到d7的排列方向0x08/0x0c
            self.write_cmd([0xBC,0X06])#扫描方向控制
        self.fill(0)
        self.show()
        self.poweron()

    def poweroff(self):
        self.write_cmd([0xAE,])

    def poweron(self):
        self.write_cmd([0xAF,])

    #可用取值范围0-511，实际有用的区间大约在245-280区间，过小是全白，过大就是全黑
    def contrast(self, contrast):
        if contrast<0x200:
            cmd=[0x81,0x0a,0x04]
            cmd[1]=contrast%64
            cmd[2]=contrast//64
            self.write_cmd(cmd)

    def invert(self, invert):
        if invert:
            self.write_cmd([0xA7,])
        else:
            self.write_cmd([0xA6,])

    def show(self):
        
        self.write_cmd([0x15,0x00,0xff])
        if self.rot==0 or self.rot==1:
            self.write_cmd([0x75,0x01,0x18]) #正向显示
        else:
            self.write_cmd([0x75,0x10,0x27]) #反向显示
        self.write_cmd([0x5C,])
        self.write_data(self.buffer)

class ST75256_I2C(ST75256):
    def __init__(self, width, height, i2c, res,addr=0x3C, rot=1):
        res.init(res.OUT, value=0)
        self.res = res
        import time
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        time.sleep_ms(10)
        self.i2c = i2c
        self.addr = addr
        self.write_list = [b"\x40", None]  # Co=0, D/C#=1
        super().__init__(width, height, rot=rot)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)
        #self.temp = bytearray(2)
        #self.temp[0] = 0xC0
        #i=0
        #while i<len(buf):
            #self.temp[1] = buf[i]
            #self.i2c.writeto(self.addr, self.temp)
            #i=i+1

    def write_cmd(self, cmd):
        self.temp = bytearray(2)
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd[0]
        self.i2c.writeto(self.addr, self.temp)
        if len(cmd)>1:
            self.write_data(bytearray(cmd[1:]))

class ST75256_SPI(ST75256):
    def __init__(self, width, height, spi, dc, res, cs, rot=1):
        dc.init(dc.OUT, value=0)
        res.init(res.OUT, value=0)
        cs.init(cs.OUT, value=1)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        #self.sck=Pin(32,Pin.OUT)
        #self.sck(1)
        #self.mosi=Pin(33,Pin.OUT)
        import time
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        time.sleep_ms(10)
        super().__init__(width, height,rot=rot)
       
    def write_cmd(self, cmd):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd[0],]))
        self.dc(1)
        if len(cmd)>1:
            self.spi.write(bytearray(cmd[1:]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)