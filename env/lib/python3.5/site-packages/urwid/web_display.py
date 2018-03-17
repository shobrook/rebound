#!/usr/bin/python
#
# Urwid web (CGI/Asynchronous Javascript) display module
#    Copyright (C) 2004-2007  Ian Ward
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

"""
Urwid web application display module
"""
import os
import sys
import signal
import random
import select
import socket
import glob

from urwid import util
_js_code = r"""
// Urwid web (CGI/Asynchronous Javascript) display module
//    Copyright (C) 2004-2005  Ian Ward
//
//    This library is free software; you can redistribute it and/or
//    modify it under the terms of the GNU Lesser General Public
//    License as published by the Free Software Foundation; either
//    version 2.1 of the License, or (at your option) any later version.
//
//    This library is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//    Lesser General Public License for more details.
//
//    You should have received a copy of the GNU Lesser General Public
//    License along with this library; if not, write to the Free Software
//    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//
// Urwid web site: http://excess.org/urwid/

colours = new Object();
colours = {
    '0': "black",
    '1': "#c00000",
    '2': "green",
    '3': "#804000",
    '4': "#0000c0",
    '5': "#c000c0",
    '6': "teal",
    '7': "silver",
    '8': "gray",
    '9': "#ff6060",
    'A': "lime",
    'B': "yellow",
    'C': "#8080ff",
    'D': "#ff40ff",
    'E': "aqua",
    'F': "white"
};

keycodes = new Object();
keycodes = {
    8: "backspace", 9: "tab", 13: "enter", 27: "esc",
    33: "page up", 34: "page down", 35: "end", 36: "home",
    37: "left", 38: "up", 39: "right", 40: "down",
    45: "insert", 46: "delete",
    112: "f1", 113: "f2", 114: "f3", 115: "f4",
    116: "f5", 117: "f6", 118: "f7", 119: "f8",
    120: "f9", 121: "f10", 122: "f11", 123: "f12"
    };

var conn = null;
var char_width = null;
var char_height = null;
var screen_x = null;
var screen_y = null;

var urwid_id = null;
var send_conn = null;
var send_queue_max = 32;
var send_queue = new Array(send_queue_max);
var send_queue_in = 0;
var send_queue_out = 0;

var check_font_delay = 1000;
var send_more_delay = 100;
var poll_again_delay = 500;

var document_location = null;

var update_method = "multipart";

var sending = false;
var lastkeydown = null;

function setup_connection() {
    if (window.XMLHttpRequest) {
        conn = new XMLHttpRequest();
    } else if (window.ActiveXObject) {
        conn = new ActiveXObject("Microsoft.XMLHTTP");
    }

    if (conn == null) {
        set_status("Connection Failed");
        alert( "Can't figure out how to send request." );
        return;
    }
    try{
        conn.multipart = true;
    }catch(e){
        update_method = "polling";
    }
    conn.onreadystatechange = handle_recv;
    conn.open("POST", document_location, true);
    conn.setRequestHeader("X-Urwid-Method",update_method);
    conn.setRequestHeader("Content-type","text/plain");
    conn.send("window resize " +screen_x+" "+screen_y+"\n");
}

function do_poll() {
    if (urwid_id == null){
        alert("that's unpossible!");
        return;
    }
    if (window.XMLHttpRequest) {
        conn = new XMLHttpRequest();
    } else if (window.ActiveXObject) {
        conn = new ActiveXObject("Microsoft.XMLHTTP");
    }
    conn.onreadystatechange = handle_recv;
    conn.open("POST", document_location, true);
    conn.setRequestHeader("X-Urwid-Method","polling");
    conn.setRequestHeader("X-Urwid-ID",urwid_id);
    conn.setRequestHeader("Content-type","text/plain");
    conn.send("eh?");
}

function handle_recv() {
    if( ! conn ){ return;}
    if( conn.readyState != 4) {
        return;
    }
    if( conn.status == 404 && urwid_id != null) {
        set_status("Connection Closed");
        return;
    }
    if( conn.status == 403 && update_method == "polling" ) {
        set_status("Server Refused Connection");
        alert("This server does not allow polling clients.\n\n" +
            "Please use a web browser with multipart support " +
            "such as Mozilla Firefox");
        return;
    }
    if( conn.status == 503 ) {
        set_status("Connection Failed");
        alert("The server has reached its maximum number of "+
            "connections.\n\nPlease try again later.");
        return;
    }
    if( conn.status != 200) {
        set_status("Connection Failed");
        alert("Error from server: "+conn.statusText);
        return;
    }
    if( urwid_id == null ){
        urwid_id = conn.getResponseHeader("X-Urwid-ID");
        if( send_queue_in != send_queue_out ){
            // keys waiting
            do_send();
        }
        if(update_method=="polling"){
            set_status("Polling");
        }else if(update_method=="multipart"){
            set_status("Connected");
        }

    }

    if( conn.responseText == "" ){
        if(update_method=="polling"){
            poll_again();
        }
        return; // keepalive
    }
    if( conn.responseText == "Z" ){
        set_status("Connection Closed");
        update_method = null;
        return;
    }

    var text = document.getElementById('text');

    var last_screen = Array(text.childNodes.length);
    for( var i=0; i<text.childNodes.length; i++ ){
        last_screen[i] = text.childNodes[i];
    }

    var frags = conn.responseText.split("\n");
    var ln = document.createElement('span');
    var k = 0;
    for( var i=0; i<frags.length; i++ ){
        var f = frags[i];
        if( f == "" ){
            var br = document.getElementById('br').cloneNode(true);
            ln.appendChild( br );
            if( text.childNodes.length > k ){
                text.replaceChild(ln, text.childNodes[k]);
            }else{
                text.appendChild(ln);
            }
            k = k+1;
            ln = document.createElement('span');
        }else if( f.charAt(0) == "<" ){
            line_number = parseInt(f.substr(1));
            if( line_number == k ){
                k = k +1;
                continue;
            }
            var clone = last_screen[line_number].cloneNode(true);
            if( text.childNodes.length > k ){
                text.replaceChild(clone, text.childNodes[k]);
            }else{
                text.appendChild(clone);
            }
            k = k+1;
        }else{
            var span=make_span(f.substr(2),f.charAt(0),f.charAt(1));
            ln.appendChild( span );
        }
    }
    for( var i=k; i < text.childNodes.length; i++ ){
        text.removeChild(last_screen[i]);
    }

    if(update_method=="polling"){
        poll_again();
    }
}

function poll_again(){
    if(conn.status == 200){
        setTimeout("do_poll();",poll_again_delay);
    }
}


function load_web_display(){
    if( document.documentURI ){
        document_location = document.documentURI;
    }else{
        document_location = document.location;
    }

    document.onkeypress = body_keypress;
    document.onkeydown = body_keydown;
    document.onresize = body_resize;

    body_resize();
    send_queue_out = send_queue_in; // don't queue the first resize

    set_status("Connecting");
    setup_connection();

    setTimeout("check_fontsize();",check_font_delay);
}

function set_status( status ){
    var s = document.getElementById('status');
    var t = document.createTextNode(status);
    s.replaceChild(t, s.firstChild);
}

function make_span(s, fg, bg){
    d = document.createElement('span');
    d.style.backgroundColor = colours[bg];
    d.style.color = colours[fg];
    d.appendChild(document.createTextNode(s));

    return d;
}

function body_keydown(e){
    if (conn == null){
        return;
    }
    if (!e) var e = window.event;
    if (e.keyCode) code = e.keyCode;
    else if (e.which) code = e.which;

    var mod = "";
    var key;

    if( e.ctrlKey ){ mod = "ctrl " + mod; }
    if( e.altKey || e.metaKey ){ mod = "meta " + mod; }
    if( e.shiftKey && e.charCode == 0 ){ mod = "shift " + mod; }

    key = keycodes[code];

    if( key != undefined ){
        lastkeydown = key;
        send_key( mod + key );
        stop_key_event(e);
        return false;
    }
}

function body_keypress(e){
    if (conn == null){
        return;
    }

    if (!e) var e = window.event;
    if (e.keyCode) code = e.keyCode;
    else if (e.which) code = e.which;

    var mod = "";
    var key;

    if( e.ctrlKey ){ mod = "ctrl " + mod; }
    if( e.altKey || e.metaKey ){ mod = "meta " + mod; }
    if( e.shiftKey && e.charCode == 0 ){ mod = "shift " + mod; }

    if( e.charCode != null && e.charCode != 0 ){
        key = String.fromCharCode(e.charCode);
    }else if( e.charCode == null ){
        key = String.fromCharCode(code);
    }else{
        key = keycodes[code];
        if( key == undefined || lastkeydown == key ){
            lastkeydown = null;
            stop_key_event(e);
            return false;
        }
    }

    send_key( mod + key );
    stop_key_event(e);
    return false;
}

function stop_key_event(e){
    e.cancelBubble = true;
    if( e.stopPropagation ){
        e.stopPropagation();
    }
    if( e.preventDefault  ){
        e.preventDefault();
    }
}

function send_key( key ){
    if( (send_queue_in+1)%send_queue_max == send_queue_out ){
        // buffer overrun
        return;
    }
    send_queue[send_queue_in] = key;
    send_queue_in = (send_queue_in+1)%send_queue_max;

    if( urwid_id != null ){
        if (send_conn == undefined || send_conn.ready_state != 4 ){
            send_more();
            return;
        }
        do_send();
    }
}

function do_send() {
    if( ! urwid_id ){ return; }
    if( ! update_method ){ return; } // connection closed
    if( send_queue_in == send_queue_out ){ return; }
    if( sending ){
        //var queue_delta = send_queue_in - send_queue_out;
        //if( queue_delta < 0 ){ queue_delta += send_queue_max; }
        //set_status("Sending (queued "+queue_delta+")");
        return;
    }
    try{
        sending = true;
        //set_status("starting send");
        if( send_conn == null ){
            if (window.XMLHttpRequest) {
                send_conn = new XMLHttpRequest();
            } else if (window.ActiveXObject) {
                send_conn = new ActiveXObject("Microsoft.XMLHTTP");
            }
        }else if( send_conn.status != 200) {
            alert("Error from server: "+send_conn.statusText);
            return;
        }else if(send_conn.readyState != 4 ){
            alert("not ready on send connection");
            return;
        }
    } catch(e) {
        alert(e);
        sending = false;
        return;
    }
    send_conn.open("POST", document_location, true);
    send_conn.onreadystatechange = send_handle_recv;
    send_conn.setRequestHeader("Content-type","text/plain");
    send_conn.setRequestHeader("X-Urwid-ID",urwid_id);
    var tmp_send_queue_in = send_queue_in;
    var out = null;
    if( send_queue_out > tmp_send_queue_in ){
        out = send_queue.slice(send_queue_out).join("\n")
        if( tmp_send_queue_in > 0 ){
            out += "\n"  + send_queue.slice(0,tmp_send_queue_in).join("\n");
        }
    }else{
        out = send_queue.slice(send_queue_out,
             tmp_send_queue_in).join("\n");
    }
    send_queue_out = tmp_send_queue_in;
    //set_status("Sending");
    send_conn.send( out +"\n" );
}

function send_handle_recv() {
    if( send_conn.readyState != 4) {
        return;
    }
    if( send_conn.status == 404) {
        set_status("Connection Closed");
        update_method = null;
        return;
    }
    if( send_conn.status != 200) {
        alert("Error from server: "+send_conn.statusText);
        return;
    }

    sending = false;

    if( send_queue_out != send_queue_in ){
        send_more();
    }
}

function send_more(){
    setTimeout("do_send();",send_more_delay);
}

function check_fontsize(){
    body_resize()
    setTimeout("check_fontsize();",check_font_delay);
}

function body_resize(){
    var t = document.getElementById('testchar');
    var t2 = document.getElementById('testchar2');
    var text = document.getElementById('text');

    var window_width;
    var window_height;
    if (window.innerHeight) {
        window_width = window.innerWidth;
        window_height = window.innerHeight;
    }else{
        window_width = document.documentElement.clientWidth;
        window_height = document.documentElement.clientHeight;
        //var z = "CI:"; for(var i in bod){z = z + " " + i;} alert(z);
    }

    char_width = t.offsetLeft / 44;
    var avail_width = window_width-18;
    var avail_width_mod = avail_width % char_width;
    var x_size = (avail_width - avail_width_mod)/char_width;

    char_height = t2.offsetTop - t.offsetTop;
    var avail_height = window_height-text.offsetTop-10;
    var avail_height_mod = avail_height % char_height;
    var y_size = (avail_height - avail_height_mod)/char_height;

    text.style.width = x_size*char_width+"px";
    text.style.height = y_size*char_height+"px";

    if( screen_x != x_size || screen_y != y_size ){
        send_key("window resize "+x_size+" "+y_size);
    }
    screen_x = x_size;
    screen_y = y_size;
}

"""

ALARM_DELAY = 60
POLL_CONNECT = 3
MAX_COLS = 200
MAX_ROWS = 100
MAX_READ = 4096
BUF_SZ = 16384

_code_colours = {
    'black':        "0",
    'dark red':        "1",
    'dark green':        "2",
    'brown':        "3",
    'dark blue':        "4",
    'dark magenta':        "5",
    'dark cyan':        "6",
    'light gray':        "7",
    'dark gray':        "8",
    'light red':        "9",
    'light green':        "A",
    'yellow':        "B",
    'light blue':        "C",
    'light magenta':    "D",
    'light cyan':        "E",
    'white':        "F",
}

# replace control characters with ?'s
_trans_table = "?" * 32 + "".join([chr(x) for x in range(32, 256)])

_css_style = """
body {    margin: 8px 8px 8px 8px; border: 0;
    color: black; background-color: silver;
    font-family: fixed; overflow: hidden; }

form { margin: 0 0 8px 0; }

#text { position: relative;
    background-color: silver;
    width: 100%; height: 100%;
    margin: 3px 0 0 0; border: 1px solid #999; }

#page { position: relative;  width: 100%;height: 100%;}
"""

# HTML Initial Page
_html_page = [
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
 "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>Urwid Web Display - ""","""</title>
<style type="text/css">
""" + _css_style + """
</style>
</head>
<body id="body" onload="load_web_display()">
<div style="position:absolute; visibility:hidden;">
<br id="br"\>
<pre>The quick brown fox jumps over the lazy dog.<span id="testchar">X</span>
<span id="testchar2">Y</span></pre>
</div>
Urwid Web Display - <b>""","""</b> -
Status: <span id="status">Set up</span>
<script type="text/javascript">
//<![CDATA[
""" + _js_code +"""
//]]>
</script>
<pre id="text"></pre>
</body>
</html>
"""]

class Screen:
    def __init__(self):
        self.palette = {}
        self.has_color = True
        self._started = False

    started = property(lambda self: self._started)

    def register_palette( self, l ):
        """Register a list of palette entries.

        l -- list of (name, foreground, background) or
             (name, same_as_other_name) palette entries.

        calls self.register_palette_entry for each item in l
        """

        for item in l:
            if len(item) in (3,4):
                self.register_palette_entry( *item )
                continue
            assert len(item) == 2, "Invalid register_palette usage"
            name, like_name = item
            if like_name not in self.palette:
                raise Exception("palette entry '%s' doesn't exist"%like_name)
            self.palette[name] = self.palette[like_name]

    def register_palette_entry( self, name, foreground, background,
        mono=None):
        """Register a single palette entry.

        name -- new entry/attribute name
        foreground -- foreground colour
        background -- background colour
        mono -- monochrome terminal attribute

        See curses_display.register_palette_entry for more info.
        """
        if foreground == "default":
            foreground = "black"
        if background == "default":
            background = "light gray"
        self.palette[name] = (foreground, background, mono)

    def set_mouse_tracking(self, enable=True):
        """Not yet implemented"""
        pass

    def tty_signal_keys(self, *args, **vargs):
        """Do nothing."""
        pass

    def start(self):
        """
        This function reads the initial screen size, generates a
        unique id and handles cleanup when fn exits.

        web_display.set_preferences(..) must be called before calling
        this function for the preferences to take effect
        """
        global _prefs

        if self._started:
            return util.StoppingContext(self)

        client_init = sys.stdin.read(50)
        assert client_init.startswith("window resize "),client_init
        ignore1,ignore2,x,y = client_init.split(" ",3)
        x = int(x)
        y = int(y)
        self._set_screen_size( x, y )
        self.last_screen = {}
        self.last_screen_width = 0

        self.update_method = os.environ["HTTP_X_URWID_METHOD"]
        assert self.update_method in ("multipart","polling")

        if self.update_method == "polling" and not _prefs.allow_polling:
            sys.stdout.write("Status: 403 Forbidden\r\n\r\n")
            sys.exit(0)

        clients = glob.glob(os.path.join(_prefs.pipe_dir,"urwid*.in"))
        if len(clients) >= _prefs.max_clients:
            sys.stdout.write("Status: 503 Sever Busy\r\n\r\n")
            sys.exit(0)

        urwid_id = "%09d%09d"%(random.randrange(10**9),
            random.randrange(10**9))
        self.pipe_name = os.path.join(_prefs.pipe_dir,"urwid"+urwid_id)
        os.mkfifo(self.pipe_name+".in",0o600)
        signal.signal(signal.SIGTERM,self._cleanup_pipe)

        self.input_fd = os.open(self.pipe_name+".in",
            os.O_NONBLOCK | os.O_RDONLY)
        self.input_tail = ""
        self.content_head = ("Content-type: "
            "multipart/x-mixed-replace;boundary=ZZ\r\n"
            "X-Urwid-ID: "+urwid_id+"\r\n"
            "\r\n\r\n"
            "--ZZ\r\n")
        if self.update_method=="polling":
            self.content_head = (
                "Content-type: text/plain\r\n"
                "X-Urwid-ID: "+urwid_id+"\r\n"
                "\r\n\r\n")

        signal.signal(signal.SIGALRM,self._handle_alarm)
        signal.alarm( ALARM_DELAY )
        self._started = True

        return util.StoppingContext(self)

    def stop(self):
        """
        Restore settings and clean up.
        """
        if not self._started:
            return

        # XXX which exceptions does this actually raise? EnvironmentError?
        try:
            self._close_connection()
        except Exception:
            pass
        signal.signal(signal.SIGTERM,signal.SIG_DFL)
        self._cleanup_pipe()
        self._started = False

    def set_input_timeouts(self, *args):
        pass

    def run_wrapper(self,fn):
        """
        Run the application main loop, calling start() first
        and stop() on exit.
        """
        try:
            self.start()
            return fn()
        finally:
            self.stop()


    def _close_connection(self):
        if self.update_method == "polling child":
            self.server_socket.settimeout(0)
            sock, addr = self.server_socket.accept()
            sock.sendall("Z")
            sock.close()

        if self.update_method == "multipart":
            sys.stdout.write("\r\nZ"
                "\r\n--ZZ--\r\n")
            sys.stdout.flush()

    def _cleanup_pipe(self, *args):
        if not self.pipe_name: return
        # XXX which exceptions does this actually raise? EnvironmentError?
        try:
            os.remove(self.pipe_name+".in")
            os.remove(self.pipe_name+".update")
        except Exception:
            pass

    def _set_screen_size(self, cols, rows ):
        """Set the screen size (within max size)."""

        if cols > MAX_COLS:
            cols = MAX_COLS
        if rows > MAX_ROWS:
            rows = MAX_ROWS
        self.screen_size = cols, rows

    def draw_screen(self, size, r ):
        """Send a screen update to the client."""

        (cols, rows) = size

        if cols != self.last_screen_width:
            self.last_screen = {}

        sendq = [self.content_head]

        if self.update_method == "polling":
            send = sendq.append
        elif self.update_method == "polling child":
            signal.alarm( 0 )
            try:
                s, addr = self.server_socket.accept()
            except socket.timeout:
                sys.exit(0)
            send = s.sendall
        else:
            signal.alarm( 0 )
            send = sendq.append
            send("\r\n")
            self.content_head = ""

        assert r.rows() == rows

        if r.cursor is not None:
            cx, cy = r.cursor
        else:
            cx = cy = None

        new_screen = {}

        y = -1
        for row in r.content():
            y += 1
            row = list(row)

            l = []

            sig = tuple(row)
            if y == cy: sig = sig + (cx,)
            new_screen[sig] = new_screen.get(sig,[]) + [y]
            old_line_numbers = self.last_screen.get(sig, None)
            if old_line_numbers is not None:
                if y in old_line_numbers:
                    old_line = y
                else:
                    old_line = old_line_numbers[0]
                send( "<%d\n"%old_line )
                continue

            col = 0
            for (a, cs, run) in row:
                run = run.translate(_trans_table)
                if a is None:
                    fg,bg,mono = "black", "light gray", None
                else:
                    fg,bg,mono = self.palette[a]
                if y == cy and col <= cx:
                    run_width = util.calc_width(run, 0,
                        len(run))
                    if col+run_width > cx:
                        l.append(code_span(run, fg, bg,
                            cx-col))
                    else:
                        l.append(code_span(run, fg, bg))
                    col += run_width
                else:
                    l.append(code_span(run, fg, bg))

            send("".join(l)+"\n")
        self.last_screen = new_screen
        self.last_screen_width = cols

        if self.update_method == "polling":
            sys.stdout.write("".join(sendq))
            sys.stdout.flush()
            sys.stdout.close()
            self._fork_child()
        elif self.update_method == "polling child":
            s.close()
        else: # update_method == "multipart"
            send("\r\n--ZZ\r\n")
            sys.stdout.write("".join(sendq))
            sys.stdout.flush()

        signal.alarm( ALARM_DELAY )


    def clear(self):
        """
        Force the screen to be completely repainted on the next
        call to draw_screen().

        (does nothing for web_display)
        """
        pass


    def _fork_child(self):
        """
        Fork a child to run CGI disconnected for polling update method.
        Force parent process to exit.
        """
        daemonize( self.pipe_name +".err" )
        self.input_fd = os.open(self.pipe_name+".in",
            os.O_NONBLOCK | os.O_RDONLY)
        self.update_method = "polling child"
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind( self.pipe_name+".update" )
        s.listen(1)
        s.settimeout(POLL_CONNECT)
        self.server_socket = s

    def _handle_alarm(self, sig, frame):
        assert self.update_method in ("multipart","polling child")
        if self.update_method == "polling child":
            # send empty update
            try:
                s, addr = self.server_socket.accept()
                s.close()
            except socket.timeout:
                sys.exit(0)
        else:
            # send empty update
            sys.stdout.write("\r\n\r\n--ZZ\r\n")
            sys.stdout.flush()
        signal.alarm( ALARM_DELAY )


    def get_cols_rows(self):
        """Return the screen size."""
        return self.screen_size

    def get_input(self, raw_keys=False):
        """Return pending input as a list."""
        l = []
        resized = False

        try:
            iready,oready,eready = select.select(
                [self.input_fd],[],[],0.5)
        except select.error as e:
            # return on interruptions
            if e.args[0] == 4:
                if raw_keys:
                    return [],[]
                return []
            raise

        if not iready:
            if raw_keys:
                return [],[]
            return []

        keydata = os.read(self.input_fd, MAX_READ)
        os.close(self.input_fd)
        self.input_fd = os.open(self.pipe_name+".in",
            os.O_NONBLOCK | os.O_RDONLY)
        #sys.stderr.write( repr((keydata,self.input_tail))+"\n" )
        keys = keydata.split("\n")
        keys[0] = self.input_tail + keys[0]
        self.input_tail = keys[-1]

        for k in keys[:-1]:
            if k.startswith("window resize "):
                ign1,ign2,x,y = k.split(" ",3)
                x = int(x)
                y = int(y)
                self._set_screen_size(x, y)
                resized = True
            else:
                l.append(k)
        if resized:
            l.append("window resize")

        if raw_keys:
            return l, []
        return l


def code_span( s, fg, bg, cursor = -1):
    code_fg = _code_colours[ fg ]
    code_bg = _code_colours[ bg ]

    if cursor >= 0:
        c_off, _ign = util.calc_text_pos(s, 0, len(s), cursor)
        c2_off = util.move_next_char(s, c_off, len(s))

        return ( code_fg + code_bg + s[:c_off] + "\n" +
             code_bg + code_fg + s[c_off:c2_off] + "\n" +
             code_fg + code_bg + s[c2_off:] + "\n")
    else:
        return code_fg + code_bg + s + "\n"


def html_escape(text):
    """Escape text so that it will be displayed safely within HTML"""
    text = text.replace('&','&amp;')
    text = text.replace('<','&lt;')
    text = text.replace('>','&gt;')
    return text


def is_web_request():
    """
    Return True if this is a CGI web request.
    """
    return 'REQUEST_METHOD' in os.environ

def handle_short_request():
    """
    Handle short requests such as passing keystrokes to the application
    or sending the initial html page.  If returns True, then this
    function recognised and handled a short request, and the calling
    script should immediately exit.

    web_display.set_preferences(..) should be called before calling this
    function for the preferences to take effect
    """
    global _prefs

    if not is_web_request():
        return False

    if os.environ['REQUEST_METHOD'] == "GET":
        # Initial request, send the HTML and javascript.
        sys.stdout.write("Content-type: text/html\r\n\r\n" +
            html_escape(_prefs.app_name).join(_html_page))
        return True

    if os.environ['REQUEST_METHOD'] != "POST":
        # Don't know what to do with head requests etc.
        return False

    if 'HTTP_X_URWID_ID' not in os.environ:
        # If no urwid id, then the application should be started.
        return False

    urwid_id = os.environ['HTTP_X_URWID_ID']
    if len(urwid_id)>20:
        #invalid. handle by ignoring
        #assert 0, "urwid id too long!"
        sys.stdout.write("Status: 414 URI Too Long\r\n\r\n")
        return True
    for c in urwid_id:
        if c not in "0123456789":
            # invald. handle by ignoring
            #assert 0, "invalid chars in id!"
            sys.stdout.write("Status: 403 Forbidden\r\n\r\n")
            return True

    if os.environ.get('HTTP_X_URWID_METHOD',None) == "polling":
        # this is a screen update request
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.connect( os.path.join(_prefs.pipe_dir,
                "urwid"+urwid_id+".update") )
            data = "Content-type: text/plain\r\n\r\n"+s.recv(BUF_SZ)
            while data:
                sys.stdout.write(data)
                data = s.recv(BUF_SZ)
            return True
        except socket.error:
            sys.stdout.write("Status: 404 Not Found\r\n\r\n")
            return True

    # this is a keyboard input request
    try:
        fd = os.open((os.path.join(_prefs.pipe_dir,
            "urwid"+urwid_id+".in")), os.O_WRONLY)
    except OSError:
        sys.stdout.write("Status: 404 Not Found\r\n\r\n")
        return True

    # FIXME: use the correct encoding based on the request
    keydata = sys.stdin.read(MAX_READ)
    os.write(fd,keydata.encode('ascii'))
    os.close(fd)
    sys.stdout.write("Content-type: text/plain\r\n\r\n")

    return True


class _Preferences:
    app_name = "Unnamed Application"
    pipe_dir = "/tmp"
    allow_polling = True
    max_clients = 20

_prefs = _Preferences()

def set_preferences( app_name, pipe_dir="/tmp", allow_polling=True,
    max_clients=20 ):
    """
    Set web_display preferences.

    app_name -- application name to appear in html interface
    pipe_dir -- directory for input pipes, daemon update sockets
                and daemon error logs
    allow_polling -- allow creation of daemon processes for
                     browsers without multipart support
    max_clients -- maximum concurrent client connections. This
               pool is shared by all urwid applications
               using the same pipe_dir
    """
    global _prefs
    _prefs.app_name = app_name
    _prefs.pipe_dir = pipe_dir
    _prefs.allow_polling = allow_polling
    _prefs.max_clients = max_clients


class ErrorLog:
    def __init__(self, errfile ):
        self.errfile = errfile
    def write(self, err):
        open(self.errfile,"a").write(err)


def daemonize( errfile ):
    """
    Detach process and become a daemon.
    """
    pid = os.fork()
    if pid:
        os._exit(0)

    os.setsid()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    os.umask(0)

    pid = os.fork()
    if pid:
        os._exit(0)

    os.chdir("/")
    for fd in range(0,20):
        try:
            os.close(fd)
        except OSError:
            pass

    sys.stdin = open("/dev/null","r")
    sys.stdout = open("/dev/null","w")
    sys.stderr = ErrorLog( errfile )

