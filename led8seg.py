import time, _thread
from machine import Pin, SPI, Timer

# LED 8 segment display

# TODO rename digit to sector
class DState:
    UNITS     = b'\xf7' #bytes([0xF7])
    TENS      = b'\xfb' #bytes([0xFB])
    HUNDREDS  = b'\xfd' #bytes([0xFD])
    THOUSANDS = b'\xfe' #bytes([0xFE])

    DigitEncoded = [UNITS, TENS, HUNDREDS, THOUSANDS]

    #   01 ----
    #   20 |  | 02
    #   40 ----    
    #   10 |  | 04
    #   08 ----     . 80

    Segments_Chars = {' ': b'\x00', '0': b'\x3f', '1': b'\x06', '2': b'\x5b', '3': b'\x4f', '4': b'\x66', '5': b'\x6d', 
                '6': b'\x7d', '7': b'\x07', '8': b'\x7f', '9': b'\x6f', 'A': b'\x77', 'b': b'\x7c', 'C': b'\x39',
                'c': b'\x58', 'd': b'\x5e', 'E': b'\x79', 'F': b'\x71', 'h': b'\x74', 'H': b'\x76', 'i': b'\x10', 
                'I': b'\x30', 'L': b'\x38', 'O': b'\x3f', 'o': b'\x5c', 'P': b'\x73', 'r': b'\x50',  'S': b'\x6d', 't': b'\x78',
                'U': b'\x3e', 'u': b'\x1c', '-': b'\x40', '|': b'\x30', '^': b'\x23', '_': b'\x08', '~': b'\x01', 
                '!': b'\x02', '/': b'\x04', '(': b'\x21', ')': b'\x03', '<': b'\x18', '>': b'\x0c', '.': b'\x80',
                '?': b'\x53', '"': b'\x36', ':': b'\x48', ';': b'\x09'}

    Segments_Dotted = {k+'.': (int.from_bytes(v, 'big') | 0x80).to_bytes(1, 'big') for k, v in Segments_Chars.items()}

    Segments = Segments_Chars | Segments_Dotted

    BLANK = Segments[' ']
    EIGHT = Segments['8']
    HYPHEN = Segments['-']

    @staticmethod
    def from_int(v, align_left=False, leading_zeros=0, dot_pos=None):
        if v < -999 or v > 9999:
            return DState.from_string("oor")
        f = "%4d" % v
        if leading_zeros == 1:
            f = "%01d" % v
        elif leading_zeros == 2:
            f = "%02d" % v
        elif leading_zeros == 3:
            f = "%03d" % v
        elif leading_zeros >= 4:
            f = "%04d" % v
            
        if align_left:
            f = "%-4d" % v

        return DState.from_string(f, align_left=align_left, dot_pos=dot_pos)

    @staticmethod
    def from_float(v, dot_pos=2):
        d = int(round(v*pow(10, max(0, dot_pos))))
        leading_zeros = dot_pos + 1
        if v < 0:
            leading_zeros = dot_pos + 2
        return DState.from_int(d, leading_zeros=leading_zeros, dot_pos=dot_pos)

    @staticmethod
    def from_string(v, align_left=False, dot_pos=None):
        dstate = DState()
        f = "%4s" % v
        if align_left:
            f = "%-4s" % v
        for pos in range(4):
            if pos == dot_pos:
                symbol = DState.Segments[f[3-pos] + '.']
            else:
                symbol = DState.Segments[f[3-pos]]
            dstate.digit(pos, symbol)
        return dstate

    @staticmethod
    def full():
        return DState()
    
    @staticmethod
    def blank():
        return DState([DState.BLANK, DState.BLANK, DState.BLANK, DState.BLANK])

    def __init__(self, digits=None):
        if digits == None:
            digits = [DState.EIGHT, DState.EIGHT, DState.EIGHT, DState.EIGHT]
        self.digits = digits

    def digit(self, pos, v):
        if type(v) == bytes:
            self.digits[pos] = v
        elif type(v) == str:
            self.digits[pos] = DState.Segments[v]
        else:
            raise ValueError(f"Wrong type of digit: {type(v)=}")
        return self
    
class DPattern:
    SWIRL1 = list()
    SWIRL1.append(DState.from_string('~   '))
    SWIRL1.append(DState.from_string(' ~  '))
    SWIRL1.append(DState.from_string('  ~ '))
    SWIRL1.append(DState.from_string('   ~'))
    SWIRL1.append(DState.from_string('   !'))
    SWIRL1.append(DState.from_string('   /'))
    SWIRL1.append(DState.from_string('   _'))
    SWIRL1.append(DState.from_string('  _ '))
    SWIRL1.append(DState.from_string(' _  '))
    SWIRL1.append(DState.from_string('_   '))
    SWIRL1.append(DState.blank().digit(3, b'\x10'))
    SWIRL1.append(DState.blank().digit(3, b'\x20'))

    SWIRL2 = list()
    SWIRL2.append(DState.from_string('~~  '))
    SWIRL2.append(DState.from_string(' ~~ '))
    SWIRL2.append(DState.from_string('  ~~'))
    SWIRL2.append(DState.from_string('   )'))
    SWIRL2.append(DState.from_string('   1'))
    SWIRL2.append(DState.from_string('   >'))
    SWIRL2.append(DState.from_string('  __'))
    SWIRL2.append(DState.from_string(' __ '))
    SWIRL2.append(DState.from_string('__  '))
    SWIRL2.append(DState.from_string('<   '))
    SWIRL2.append(DState.from_string('|   '))
    SWIRL2.append(DState.from_string('(   '))

    LINE1 = list()
    LINE1.append(DState.from_string('-   '))
    LINE1.append(DState.from_string(' -  '))
    LINE1.append(DState.from_string('  - '))
    LINE1.append(DState.from_string('   -'))


    CHARGE1 = list()
    CHARGE1.append(DState.from_string('    '))
    CHARGE1.append(DState.from_string('-   '))
    CHARGE1.append(DState.from_string('--  '))
    CHARGE1.append(DState.from_string('--- '))
    CHARGE1.append(DState.from_string('----'))

    CHARGE2 = list()
    CHARGE2.append(DState.from_string('    '))
    CHARGE2.append(DState.from_string('|   '))
    CHARGE2.append(DState.from_string('"   '))
    CHARGE2.append(DState.from_string('"|  '))
    CHARGE2.append(DState.from_string('""  '))
    CHARGE2.append(DState.from_string('""| '))
    CHARGE2.append(DState.from_string('""" '))
    CHARGE2.append(DState.from_string('"""|'))
    CHARGE2.append(DState.from_string('""""'))


# TODO rename screen to frame
class DDisplay:
    def __init__(self, cs_pin=9, screen_time=2.5):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs(1)
        self.screens = [DState()]
        self.screen_time = screen_time

    def value(self, dstate, screen_no=0):
        if screen_no >= 100:
            raise ValueError(f"Too many screens: {screen_no=}")
        for i in range(100):
            if screen_no >= len(self.screens):
                self.screens.append(DState())
            else:
                break
        self.screens[screen_no] = dstate

    def values(self, dstates):
        self.screens = dstates
    


class DDriver:
    def __init__(self, mosi_pin=11, sck_pin=10, brightness=0.5, freq=60, screen_time=1.5):
        self.counter = 0
        self.freq = freq
        self.brightness = brightness
        # in microseconds
        self.brightness_period = round(60000 * self.brightness // self.freq)
        self.display = [DDisplay(screen_time=screen_time)]
        self.spi = SPI(1, 10_000_000, polarity=0, phase=0, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=None)
        # self.display_timer = Timer()
        # self.display_timer.init(freq=freq, mode=Timer.PERIODIC, callback=self.show)
        # run on the separate CPU core1 to prevent flickering caused by interference by other tasks
        _thread.start_new_thread(self.loop, ())


    def value(self, dstate, screen_no=0, display_no=0):
        # TODO if display_no >= len(self.display): extend list
        self.display[display_no].value(dstate, screen_no=screen_no)

    def values(self, dstates, display_no=0):
        # TODO if display_no >= len(self.display): extend list
        self.display[display_no].values(dstates)

    # this method runs up to 100 times per second
    # so it must optimized for garbage collector
    # focus on not allocating memory, so that gc is not run often as it makes display flickering
    def show(self, timer=None):
        self.counter += 1
        # if self.counter % 200 == 0:
        #     print(f"led8seg.show: {_thread.get_ident()=}")
        for disp in self.display:
            # determine which frame to display
            frameno = (self.counter // round(self.freq * disp.screen_time)) % len(disp.screens)
            frame = disp.screens[frameno]
            for pos in range(4):
                disp.cs(0)
                # indicate which digit position to write
                self.spi.write(DState.DigitEncoded[pos])
                # can display only a single digit at any moment
                self.spi.write(frame.digits[pos])
                disp.cs(1)
                time.sleep_us(self.brightness_period)
                disp.cs(0)
                self.spi.write(DState.DigitEncoded[pos])
                self.spi.write(DState.BLANK)
                disp.cs(1)

    # run that loop on CPU core1 to prevent glitches caused by other tasks interference
    def loop(self):
        while(True):
            start = time.ticks_us()
            self.show()
            elapsed_us = time.ticks_diff(time.ticks_us(), start)
            time.sleep_us(1000000//self.freq-elapsed_us)


def main():
    driver = DDriver(brightness=0.5, screen_time=2.0)
    time.sleep(1)
    driver.value(DState.blank())
    time.sleep(1)

    print(f"led main: {_thread.get_ident()=}")

    # ds1 = DState.from_float(-3.45678, dot_pos=1)
    # ds1.digit(3, DState.Segments['P'])
    # driver.value(ds1)
    # time.sleep(1)

    # ds2 = DState.from_int(9999)
    # driver.value(ds2, screen_no=0)
    # ds3 = DState.from_int(8888)
    # driver.value(ds3, screen_no=1)
    # time.sleep(400)

    # driver.values(DPattern.SWIRL2)


    # driver.value(DState.from_int(1, leading_zeros=0), screen_no=0)
    # driver.value(DState.from_int(2, leading_zeros=1), screen_no=1)
    # driver.value(DState.from_int(3, leading_zeros=2), screen_no=2)
    # driver.value(DState.from_int(4, leading_zeros=3), screen_no=3)
    # driver.value(DState.from_int(5, leading_zeros=4), screen_no=4)



    # driver.value(DState.from_float(0.001, dot_pos=3), screen_no=0)
    # driver.value(DState.from_float(0.021, dot_pos=3), screen_no=1)
    # driver.value(DState.from_float(0.321, dot_pos=3), screen_no=2)
    # driver.value(DState.from_float(4.321, dot_pos=3), screen_no=3)
    # driver.value(DState.from_float(0.01, dot_pos=2), screen_no=0)
    # driver.value(DState.from_float(0.21, dot_pos=2), screen_no=1)
    # driver.value(DState.from_float(3.21, dot_pos=2), screen_no=2)
    # driver.value(DState.from_float(43.21, dot_pos=2), screen_no=3)
    # driver.value(DState.from_float(0.1, dot_pos=1), screen_no=0)
    # driver.value(DState.from_float(2.1, dot_pos=1), screen_no=1)
    # driver.value(DState.from_float(32.1, dot_pos=1), screen_no=2)
    # driver.value(DState.from_float(432.1, dot_pos=1), screen_no=3)

    # driver.value(DState.from_float(-0.001, dot_pos=3), screen_no=0)
    # driver.value(DState.from_float(-0.021, dot_pos=3), screen_no=1)
    # driver.value(DState.from_float(-0.321, dot_pos=3), screen_no=2)
    # driver.value(DState.from_float(-4.321, dot_pos=3), screen_no=3)
    # driver.value(DState.from_float(-0.01, dot_pos=2), screen_no=0)
    # driver.value(DState.from_float(-0.21, dot_pos=2), screen_no=1)
    # driver.value(DState.from_float(-3.21, dot_pos=2), screen_no=2)
    # driver.value(DState.from_float(-43.21, dot_pos=2), screen_no=3)
    # driver.value(DState.from_float(-0.1, dot_pos=1), screen_no=0)
    # driver.value(DState.from_float(-2.1, dot_pos=1), screen_no=1)
    # driver.value(DState.from_float(-32.1, dot_pos=1), screen_no=2)
    # driver.value(DState.from_float(-432.1, dot_pos=1), screen_no=3)


    print("Wait forever")
    time.sleep(1000000000)


if __name__ == "__main__":
    main()
    

