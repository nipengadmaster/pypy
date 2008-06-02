"""
PyBoy GameBoy (TM) Emulator
 
Timer and Divider
"""

from pypy.lang.gameboy import constants
from pypy.lang.gameboy.interrupt import *
from math import ceil
from pypy.lang.gameboy.ram import iMemory
import time
import math


class Timer(iMemory):

    def __init__(self, interrupt):
        assert isinstance(interrupt, Interrupt)
        self.interrupt = interrupt
        self.reset()

    def reset(self):
        self.div            = 0
        self.divider_cycles = constants.DIV_CLOCK
        self.tima           = 0
        self.tma            = 0
        self.tac            = 0
        self.timer_cycles   = constants.TIMER_CLOCK[0]
        self.timer_clock    = constants.TIMER_CLOCK[0]

    def write(self,  address, data):
        address = int(address)
        if address == constants.DIV:
            self.set_divider(data)
        elif address == constants.TIMA:
            self.set_timer_counter(data)
        elif address == constants.TMA:
            self.set_timer_modulo(data)
        elif address == constants.TAC:
            self.set_timer_control(data)
    
    def read(self,  address):
        address = int(address)
        if address == constants.DIV:
            return self.get_divider()
        elif address == constants.TIMA:
            return self.get_timer_counter()
        elif address == constants.TMA:
            return self.get_timer_modulo()
        elif address == constants.TAC:
            return self.get_timer_control()
        return 0xFF

    def get_divider(self):
        return self.div
    
    def set_divider(self,  data): 
        """ DIV register resets on write """
        self.div = 0

    def get_timer_counter(self):
        return self.tima
    
    def set_timer_counter(self,  data):
        self.tima = data

    def get_timer_modulo(self):
        return self.tma
    
    def set_timer_modulo(self,  data):
        self.tma = data

    def get_timer_control(self):
        return 0xF8 | self.tac

    def set_timer_control(self,  data):
        if (self.tac & 0x03) != (data & 0x03):
            self.timer_clock  = constants.TIMER_CLOCK[data & 0x03]
            self.timer_cycles = constants.TIMER_CLOCK[data & 0x03]
        self.tac = data

    def get_cycles(self):
        if (self.tac & 0x04) != 0 and self.timer_cycles < self.divider_cycles:
                return self.timer_cycles
        return self.divider_cycles

    def emulate(self,  ticks):
        self.emulate_divider(ticks)
        self.emulate_timer(ticks)

    def emulate_divider(self,  ticks):
        self.divider_cycles -= ticks
        if self.divider_cycles > 0:
            return
        count = int(math.ceil(-self.divider_cycles / constants.DIV_CLOCK)+1)
        self.divider_cycles += count*constants.DIV_CLOCK
        self.div = (self.div + count) % (0xFF+1);
            
    def emulate_timer(self,  ticks):
        if (self.tac & 0x04) == 0:
            return
        self.timer_cycles -= ticks
        while self.timer_cycles <= 0:
            self.tima = (self.tima + 1) & 0xFF
            self.timer_cycles += self.timer_clock
            if self.tima == 0x00:
                self.tima = self.tma
                self.interrupt.raise_interrupt(constants.TIMER)
    
    #def emulate_timer(self,  ticks):
    #    if (self.tac & 0x04) == 0:
    #        return
    #    self.timer_cycles -= ticks
    #    if self.timer_cycles > 0: return
    #    count = int(math.ceil(-self.timer_cycles / self.timer_clock)) + 1
    #    self.timer_cycles += self.timer_clock*count
    #    # check for zero pass
    #    if (self.tima + count) > 0xFF:
    #        self.interrupt.raise_interrupt(constants.TIMER)
    #        zero_passes = math.ceil(self.tima / count)
    #        self.tima = (self.tma + count - zero_passes ) % (0xFF +1)
    #    else:
    #        self.tima = (self.tima + count) % (0xFF +1)
# CLOCK DRIVER -----------------------------------------------------------------

class Clock(object):
    
    def __init__(self):
        pass
    
    def get_time(self):
        return int(time.time()*1000)
        
