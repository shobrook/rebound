#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Urwid LCD display module
#    Copyright (C) 2010  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

from __future__ import division, print_function

from .display_common import BaseScreen

import time

class LCDScreen(BaseScreen):
    def set_terminal_properties(self, colors=None, bright_is_bold=None,
        has_underline=None):
        pass

    def set_mouse_tracking(self, enable=True):
        pass

    def set_input_timeouts(self, *args):
        pass

    def reset_default_terminal_palette(self, *args):
        pass

    def draw_screen(self, size, r ):
        pass

    def clear(self):
        pass

    def get_cols_rows(self):
        return self.DISPLAY_SIZE



class CFLCDScreen(LCDScreen):
    """
    Common methods for Crystal Fontz LCD displays
    """
    KEYS = [None, # no key with code 0
        'up_press', 'down_press', 'left_press',
        'right_press', 'enter_press', 'exit_press',
        'up_release', 'down_release', 'left_release',
        'right_release', 'enter_release', 'exit_release',
        'ul_press', 'ur_press', 'll_press', 'lr_press',
        'ul_release', 'ur_release', 'll_release', 'lr_release']
    CMD_PING = 0
    CMD_VERSION = 1
    CMD_CLEAR = 6
    CMD_CGRAM = 9
    CMD_CURSOR_POSITION = 11 # data = [col, row]
    CMD_CURSOR_STYLE = 12 # data = [style (0-4)]
    CMD_LCD_CONTRAST = 13 # data = [contrast (0-255)]
    CMD_BACKLIGHT = 14 # data = [power (0-100)]
    CMD_LCD_DATA = 31 # data = [col, row] + text
    CMD_GPO = 34 # data = [pin(0-12), value(0-100)]

    # sent from device
    CMD_KEY_ACTIVITY = 0x80
    CMD_ACK = 0x40  # in high two bits ie. & 0xc0

    CURSOR_NONE = 0
    CURSOR_BLINKING_BLOCK = 1
    CURSOR_UNDERSCORE = 2
    CURSOR_BLINKING_BLOCK_UNDERSCORE = 3
    CURSOR_INVERTING_BLINKING_BLOCK = 4

    MAX_PACKET_DATA_LENGTH = 22

    colors = 1
    has_underline = False

    def __init__(self, device_path, baud):
        """
        device_path -- eg. '/dev/ttyUSB0'
        baud -- baud rate
        """
        super(CFLCDScreen, self).__init__()
        self.device_path = device_path
        from serial import Serial
        self._device = Serial(device_path, baud, timeout=0)
        self._unprocessed = ""


    @classmethod
    def get_crc(cls, buf):
        # This seed makes the output of this shift based algorithm match
        # the table based algorithm. The center 16 bits of the 32-bit
        # "newCRC" are used for the CRC. The MSB of the lower byte is used
        # to see what bit was shifted out of the center 16 bit CRC
        # accumulator ("carry flag analog");
        newCRC = 0x00F32100
        for byte in buf:
            # Push this byte’s bits through a software
            # implementation of a hardware shift & xor.
            for bit_count in range(8):
                # Shift the CRC accumulator
                newCRC >>= 1
                # The new MSB of the CRC accumulator comes
                # from the LSB of the current data byte.
                if ord(byte) & (0x01 << bit_count):
                    newCRC |= 0x00800000
                # If the low bit of the current CRC accumulator was set
                # before the shift, then we need to XOR the accumulator
                # with the polynomial (center 16 bits of 0x00840800)
                if newCRC & 0x00000080:
                    newCRC ^= 0x00840800
        # All the data has been done. Do 16 more bits of 0 data.
        for bit_count in range(16):
            # Shift the CRC accumulator
            newCRC >>= 1
            # If the low bit of the current CRC accumulator was set
            # before the shift we need to XOR the accumulator with
            # 0x00840800.
            if newCRC & 0x00000080:
                newCRC ^= 0x00840800
        # Return the center 16 bits, making this CRC match the one’s
        # complement that is sent in the packet.
        return ((~newCRC)>>8) & 0xffff

    def _send_packet(self, command, data):
        """
        low-level packet sending.
        Following the protocol requires waiting for ack packet between
        sending each packet to the device.
        """
        buf = chr(command) + chr(len(data)) + data
        crc = self.get_crc(buf)
        buf = buf + chr(crc & 0xff) + chr(crc >> 8)
        self._device.write(buf)

    def _read_packet(self):
        """
        low-level packet reading.
        returns (command/report code, data) or None

        This method stored data read and tries to resync when bad data
        is received.
        """
        # pull in any new data available
        self._unprocessed = self._unprocessed + self._device.read()
        while True:
            try:
                command, data, unprocessed = self._parse_data(self._unprocessed)
                self._unprocessed = unprocessed
                return command, data
            except self.MoreDataRequired:
                return
            except self.InvalidPacket:
                # throw out a byte and try to parse again
                self._unprocessed = self._unprocessed[1:]

    class InvalidPacket(Exception):
        pass
    class MoreDataRequired(Exception):
        pass

    @classmethod
    def _parse_data(cls, data):
        """
        Try to read a packet from the start of data, returning
        (command/report code, packet_data, remaining_data)
        or raising InvalidPacket or MoreDataRequired
        """
        if len(data) < 2:
            raise cls.MoreDataRequired
        command = ord(data[0])
        plen = ord(data[1])
        if plen > cls.MAX_PACKET_DATA_LENGTH:
            raise cls.InvalidPacket("length value too large")
        if len(data) < plen + 4:
            raise cls.MoreDataRequired
        crc = cls.get_crc(data[:2 + plen])
        pcrc = ord(data[2 + plen]) + (ord(data[3 + plen]) << 8 )
        if crc != pcrc:
            raise cls.InvalidPacket("CRC doesn't match")
        return (command, data[2:2 + plen], data[4 + plen:])



class KeyRepeatSimulator(object):
    """
    Provide simulated repeat key events when given press and
    release events.

    If two or more keys are pressed disable repeating until all
    keys are released.
    """
    def __init__(self, repeat_delay, repeat_next):
        """
        repeat_delay -- seconds to wait before starting to repeat keys
        repeat_next -- time between each repeated key
        """
        self.repeat_delay = repeat_delay
        self.repeat_next = repeat_next
        self.pressed = {}
        self.multiple_pressed = False

    def press(self, key):
        if self.pressed:
            self.multiple_pressed = True
        self.pressed[key] = time.time()

    def release(self, key):
        if key not in self.pressed:
            return # ignore extra release events
        del self.pressed[key]
        if not self.pressed:
            self.multiple_pressed = False

    def next_event(self):
        """
        Return (remaining, key) where remaining is the number of seconds
        (float) until the key repeat event should be sent, or None if no
        events are pending.
        """
        if len(self.pressed) != 1 or self.multiple_pressed:
            return
        for key in self.pressed:
            return max(0, self.pressed[key] + self.repeat_delay
                - time.time()), key

    def sent_event(self):
        """
        Cakk this method when you have sent a key repeat event so the
        timer will be reset for the next event
        """
        if len(self.pressed) != 1:
            return # ignore event that shouldn't have been sent
        for key in self.pressed:
            self.pressed[key] = (
                time.time() - self.repeat_delay + self.repeat_next)
            return


class CF635Screen(CFLCDScreen):
    u"""
    Crystal Fontz 635 display

    20x4 character display + cursor
    no foreground/background colors or settings supported

    see CGROM for list of close unicode matches to characters available

    6 button input
    up, down, left, right, enter (check mark), exit (cross)
    """
    DISPLAY_SIZE = (20, 4)

    # ① through ⑧ are programmable CGRAM (chars 0-7, repeated at 8-15)
    # double arrows (⇑⇓) appear as double arrowheads (chars 18, 19)
    # ⑴ resembles a bell
    # ⑵ resembles a filled-in "Y"
    # ⑶ is the letters "Pt" together
    # partial blocks (▇▆▄▃▁) are actually shorter versions of (▉▋▌▍▏)
    #   both groups are intended to draw horizontal bars with pixel
    #   precision, use ▇*[▆▄▃▁]? for a thin bar or ▉*[▋▌▍▏]? for a thick bar
    CGROM = (
        u"①②③④⑤⑥⑦⑧①②③④⑤⑥⑦⑧"
        u"►◄⇑⇓«»↖↗↙↘▲▼↲^ˇ█"
        u" !\"#¤%&'()*+,-./"
        u"0123456789:;<=>?"
        u"¡ABCDEFGHIJKLMNO"
        u"PQRSTUVWXYZÄÖÑÜ§"
        u"¿abcdefghijklmno"
        u"pqrstuvwxyzäöñüà"
        u"⁰¹²³⁴⁵⁶⁷⁸⁹½¼±≥≤μ"
        u"♪♫⑴♥♦⑵⌜⌟“”()αɛδ∞"
        u"@£$¥èéùìòÇᴾØøʳÅå"
        u"⌂¢ΦτλΩπΨΣθΞ♈ÆæßÉ"
        u"ΓΛΠϒ_ÈÊêçğŞşİι~◊"
        u"▇▆▄▃▁ƒ▉▋▌▍▏⑶◽▪↑→"
        u"↓←ÁÍÓÚÝáíóúýÔôŮů"
        u"ČĔŘŠŽčĕřšž[\]{|}")

    cursor_style = CFLCDScreen.CURSOR_INVERTING_BLINKING_BLOCK

    def __init__(self, device_path, baud=115200,
            repeat_delay=0.5, repeat_next=0.125,
            key_map=['up', 'down', 'left', 'right', 'enter', 'esc']):
        """
        device_path -- eg. '/dev/ttyUSB0'
        baud -- baud rate
        repeat_delay -- seconds to wait before starting to repeat keys
        repeat_next -- time between each repeated key
        key_map -- the keys to send for this device's buttons
        """
        super(CF635Screen, self).__init__(device_path, baud)

        self.repeat_delay = repeat_delay
        self.repeat_next = repeat_next
        self.key_repeat = KeyRepeatSimulator(repeat_delay, repeat_next)
        self.key_map = key_map

        self._last_command = None
        self._last_command_time = 0
        self._command_queue = []
        self._screen_buf = None
        self._previous_canvas = None
        self._update_cursor = False


    def get_input_descriptors(self):
        """
        return the fd from our serial device so we get called
        on input and responses
        """
        return [self._device.fd]

    def get_input_nonblocking(self):
        """
        Return a (next_input_timeout, keys_pressed, raw_keycodes)
        tuple.

        The protocol for our device requires waiting for acks between
        each command, so this method responds to those as well as key
        press and release events.

        Key repeat events are simulated here as the device doesn't send
        any for us.

        raw_keycodes are the bytes of messages we received, which might
        not seem to have any correspondence to keys_pressed.
        """
        input = []
        raw_input = []
        timeout = None

        while True:
            packet = self._read_packet()
            if not packet:
                break
            command, data = packet

            if command == self.CMD_KEY_ACTIVITY and data:
                d0 = ord(data[0])
                if 1 <= d0 <= 12:
                    release = d0 > 6
                    keycode = d0 - (release * 6) - 1
                    key = self.key_map[keycode]
                    if release:
                        self.key_repeat.release(key)
                    else:
                        input.append(key)
                        self.key_repeat.press(key)
                    raw_input.append(d0)

            elif command & 0xc0 == 0x40: # "ACK"
                if command & 0x3f == self._last_command:
                    self._send_next_command()

        next_repeat = self.key_repeat.next_event()
        if next_repeat:
            timeout, key = next_repeat
            if not timeout:
                input.append(key)
                self.key_repeat.sent_event()
                timeout = None

        return timeout, input, []


    def _send_next_command(self):
        """
        send out the next command in the queue
        """
        if not self._command_queue:
            self._last_command = None
            return
        command, data = self._command_queue.pop(0)
        self._send_packet(command, data)
        self._last_command = command # record command for ACK
        self._last_command_time = time.time()

    def queue_command(self, command, data):
        self._command_queue.append((command, data))
        # not waiting? send away!
        if self._last_command is None:
            self._send_next_command()

    def draw_screen(self, size, canvas):
        assert size == self.DISPLAY_SIZE

        if self._screen_buf:
            osb = self._screen_buf
        else:
            osb = []
        sb = []

        y = 0
        for row in canvas.content():
            text = []
            for a, cs, run in row:
                text.append(run)
            if not osb or osb[y] != text:
                self.queue_command(self.CMD_LCD_DATA, chr(0) + chr(y) +
                    "".join(text))
            sb.append(text)
            y += 1

        if (self._previous_canvas and
                self._previous_canvas.cursor == canvas.cursor and
                (not self._update_cursor or not canvas.cursor)):
            pass
        elif canvas.cursor is None:
            self.queue_command(self.CMD_CURSOR_STYLE, chr(self.CURSOR_NONE))
        else:
            x, y = canvas.cursor
            self.queue_command(self.CMD_CURSOR_POSITION, chr(x) + chr(y))
            self.queue_command(self.CMD_CURSOR_STYLE, chr(self.cursor_style))

        self._update_cursor = False
        self._screen_buf = sb
        self._previous_canvas = canvas

    def program_cgram(self, index, data):
        """
        Program character data.  Characters available as chr(0) through
        chr(7), and repeated as chr(8) through chr(15).

        index -- 0 to 7 index of character to program

        data -- list of 8, 6-bit integer values top to bottom with MSB
        on the left side of the character.
        """
        assert 0 <= index <= 7
        assert len(data) == 8
        self.queue_command(self.CMD_CGRAM, chr(index) +
            "".join([chr(x) for x in data]))

    def set_cursor_style(self, style):
        """
        style -- CURSOR_BLINKING_BLOCK, CURSOR_UNDERSCORE,
            CURSOR_BLINKING_BLOCK_UNDERSCORE or
            CURSOR_INVERTING_BLINKING_BLOCK
        """
        assert 1 <= style <= 4
        self.cursor_style = style
        self._update_cursor = True

    def set_backlight(self, value):
        """
        Set backlight brightness

        value -- 0 to 100
        """
        assert 0 <= value <= 100
        self.queue_command(self.CMD_BACKLIGHT, chr(value))

    def set_lcd_contrast(self, value):
        """
        value -- 0 to 255
        """
        assert 0 <= value <= 255
        self.queue_command(self.CMD_LCD_CONTRAST, chr(value))

    def set_led_pin(self, led, rg, value):
        """
        led -- 0 to 3
        rg -- 0 for red, 1 for green
        value -- 0 to 100
        """
        assert 0 <= led <= 3
        assert rg in (0, 1)
        assert 0 <= value <= 100
        self.queue_command(self.CMD_GPO, chr(12 - 2 * led - rg) +
            chr(value))

