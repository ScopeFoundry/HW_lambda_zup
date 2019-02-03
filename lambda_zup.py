from __future__ import division
import serial
import time
import re
import threading

class LambdaZup(object):
    """ TDK-Lambda Zup Programmable DC Power Supply
    
        RS232 / RS485 Interface
    
    """
    
    
    def __init__(self, port="COM1", address=0x01, always_send_address = True, debug=False):
        self.port = port
        self.address = address
        self.debug =debug
        self.always_send_address = always_send_address
        
        self.lock = threading.RLock()

        
        """If port is a Serial object (or other file-like object)
        use it instead of creating a new serial port"""
        if hasattr(port, 'read'):
            self.ser = self.port
            self.port = None
        else:        
            self.ser = serial.Serial(self.port, baudrate = 9600, bytesize=8, parity='N', 
                    stopbits=1, xonxoff=1, rtscts=0, timeout=0.5)
        
        #if not self.always_send_address:
        self.set_address()
        
        self.get_software_revision()
        
    def close(self):
        self.ser.close()
        
    def _write(self, cmd):
        assert cmd[0] == ':'
        assert cmd[-1] == ';'
        
        with self.lock:
            if self.always_send_address:
                if self.debug: "sending address", self.address
                adrcmd = ":ADR%02i;" % self.address
                self.ser.write(adrcmd.encode())
                time.sleep(0.050)
            
            if self.debug: print( "write: ", cmd)
            
            self.ser.write(cmd.encode())

    def _ask(self, cmd):
        "call and response via serial port"
        with self.lock:
            self._write(cmd)
            #time.sleep(0.010)
            resp = self.ser.readline().decode()
        resp = resp.rstrip()  #strip end of line characters "\r\n"
        if self.debug: print("ask response:", repr(resp))
        return resp
        
        
    
    #### 5.5.1 Initialization control
    
    def set_address(self,adr=None):
        """
        Sets the power supply address with which you are communicating.
            ADR is followed by the address which can be 01 to 31.
            Does not change the internal address of current supply. This can only be done
            by the front panel of the supply.
        """
        if not adr:
            adr = self.address
        adr = int(adr)
        assert 0 < adr < 32
        
        self._write(":ADR%02i;" % adr)
        time.sleep(0.050)
        self.address = adr
        
        return self.address
    
    def clear_comm_buffer(self):
        """Clears the communication buffer and the following registers:
                1. Operational status register
                2. Alarm (fault) status register
                3. Programming error register
        """
        self._write(":DCL;")
        
    def set_remote_mode(self, mode=0):
        """
        Sets the power supply to local or remote mode. (This command is active when the
            unit is either in Local or Remote modes).Transition from Local to Remote mode
            is made via the front panel only.
            :RMT0; Transition from Remote to Local mode.
            :RMT1; Transition from latched Remote to non-latched Remote.
            :RMT2; Latched remote: Transition back to Local mode or to non-latched
                    Remote can be made via the serial port (RS232/485).
                    At this mode, the front panel Local/Rem function is disabled.
                    Escape from this mode to non -latched remote mode can be made by
                    turning the AC ON/OFF to OFF and after approx. 10sec.to ON again.
        """
        if   mode == "local":
            mode = 0
        elif mode == "non-latched":
            mode = 1
        elif mode == "latched":
            mode = 2
        assert mode in [0,1,2]
        self._write(":RMT%i;" % mode)
        
    
    def get_remote_mode(self):
        """
        Returns the remote/local setting. The returned data is an ASCII string.
            RM1 (Theunitisinremotemode)
            RM2 (Theunitisinlatchedremotemode)
        """
        self.remote_mode = self._ask(":RMT?;")
        return self.remote_mode
    
    #### 5.5.2 ID control commands
    def get_model(self):
        """
        Returns the power supply model identification as an ASCII string: Nemic-Lambda ZUP(XXV)-(YYA).
        XX - The rated output voltage
        YY - The rated output current
        example: Nemic-Lambda ZUP(6V-33A)
        """
        self.model = self._ask(":MDL?;")
        return self.model
    
    def get_software_revision(self):
        """
        Returns the software version as an ASCII string: Ver XX-YY A.B
        XX- The rated output voltage
        YY- The rated output current
        A.B- Version identifier example: Ver 6-33 1.0
        
        python: stores the max_voltage and max_current as well
        """
        out = self._ask(":REV?;")
        
        ver, maxV, maxA, revision = out.replace('-', ' ').split()
        
        self.max_voltage = int(maxV)
        self.max_current = float(maxA)
        self.software_revision = revision
        
        return self.software_revision    
    
    #### 5.5.3 Output control
    
    def set_voltage(self, volt):
        """
        Sets the output voltage value in volts. This programmed voltage is the actual
        output at constant-voltage mode or the voltage limit at constant current mode.
        The range of the voltage values are as shown in table 5-1. Use all digits for voltage programming

        Model 	    MIN. 	MAX. 
        ZUP6-XY 	0.000	6.000
        ZUP10-XY 	00.000	10.000
        ZUP20-XY 	00.000	20.000
        ZUP36-XY 	00.00	36.00
        ZUP60-XY 	00.00	60.00
        ZUP80-XY 	00.00	80.00
        ZUP120-XY 	000.00	120.00
        Table 5-1: Voltage programming range. Example - ZUP6-XY :VOL5.010;
        
        Note:
        The ZUP can accept programmed value higher by up to 5% than the table values, however it is not recommended to program power supply over the rated voltage.
        ZUP10-XY :VOL08.500;
        """
        assert 0 <= volt <= self.max_voltage

        fmt_str = v_format_strs[self.max_voltage]
        self._write(":VOL{};".format(fmt_str).format(volt))
    
    def get_voltage_setp(self):
        """ Returns the string SV(Set Voltage) followed by the present programmed output 
        voltage value. The actual voltage range is as shown in table 5-1.
        example: SV5.010 SV08.500

        python: converts result to float
        """
    
        out = self._ask(":VOL!;")
        assert out[:2] == "SV"
        self.voltage_setp = float(out[2:])
        return self.voltage_setp
        
    def get_voltage_actual(self):
        """ Returns the string AV(Actual Voltage) followed by the actual output voltage.
        The actual voltage range is the same as the programming range.
        example: AV5.010 AV08.500
        
        python: converts result to float
        """
    
        out = self._ask(":VOL?;")
        assert out[:2] == "AV"
        self.voltage_actual = float(out[2:])
        return self.voltage_actual
        
    def set_current(self, amp):
        """
        Sets the output current in Amperes. This programmed current is the actual output
        current at constant-current mode or the current limit at constant voltage mode.
        The programming range is shown in table 5-2:
        Use all digits for current programming.
        
        Example - ZUP60-3.5 :CUR3.000; ZUP10-40 :CUR07.50;        
        
        Model       MIN.        MAX.
        ZUP6-33     00.00      33.00
        ZUP6-66     00.00      66.00
        ZUP6-132    000.00     132.00
        ZUP10-20    00.000     20.000
        ZUP10-40    00.00      40.00
        ZUP10-80    00.00      80.00
        ZUP20-10    00.000     10.000
        ZUP20-20    00.000     20.000
        ZUP20-40    00.00      40.00
        ZUP36-6     0.000      6.000
        ZUP36-12    00.000     12.000
        ZUP36-24    00.000     24.000
        ZUP60-3.5   0.000      3.500
        ZUP60-7     0.000      7.000
        ZUP60-14    00.000     14.000
        ZUP80-2.5   0.0000     2.5000
        ZUP80-5     0.000      5.000
        ZUP120-1.8  0.0000     1.8000
        ZUP120-3.6  0.000      3.600
        
        Note:
            The ZUP can accept values higher by 5% thantherating.Itis recommended to
            set the output current to 105% of the rating if the unit is required to 
            supply the rated current.
        """
        
        assert 0 <= amp <= self.max_current
        # this only has the correct decimal points for ZUP6-33
        # self._write(":CUR%02.3f;" % amp)
        
        fmt_str = i_format_strs[(self.max_voltage, self.max_current)]
        self._write(":CUR{};".format(fmt_str).format(amp))
        
    def get_current_setp(self):
        """
        Returns the string SA(Set Amper) followed by the present programmed output
        current. The programmed value range is shown in table 5-2.
        example- SA3.000 SA07.50

        python: converts result to float
        """
        
        out = self._ask(":CUR!;")
        assert out[:2] == "SA"
        self.current_setp = float(out[2:])
        return self.current_setp
    
    def get_current_actual(self):
        """
        Returns the string AA(Actual Amper) followed by the actual output current.
        The actual current range is the same as the programming range.
        example- AA3.000 AA07.50

        python: converts result to float
        """
        out = self._ask(":CUR?;")
        assert out[:2] == "AA"
        self.current_actual = float(out[2:])
        return self.current_actual
    
    def set_output(self, outp=True):
        """
        Sets the output to On or Off.
        :OUT1; - Output On
        :OUT0; - Output Off
        
        python: takes a boolean outp
        """
        if outp:
            self._write(":OUT1;")
        else:
            self._write(":OUT0;")
    
    def get_output(self):
        """
        Returns OT followed by the output On/Off status.
        OT1 - Output is On
        OT0 - Output is Off

        python: converts result to boolean
        """
        out = self._ask(":OUT?;")
        assert out[:2] == "OT"
        if out == "OT1":
            self.output = True
        elif out == "OT0":
            self.output = False
        else:
            raise ValueError
        return self.output

    def set_foldback_protection(self, fld=1):
        """
        Sets the Foldback protection to On or Off.
            :FLD1; Arm thefoldbackprotection.
            :FLD0; Release the foldback protection.
            :FLD2; Cancel the foldback protection.
        When the foldback protection is activated, 
        :FLD0; will release the protection and re-arm it 
        while :FLD2; will cancel the protection. 
        If the protection has not been activated, both commands are the same.
        """
        if fld in [True, 1, "arm"]:
            self._write(":FLD1;")
        elif fld in [False, 0, "release"]:
            self._write(":FLD0;")
        elif fld in [2, "cancel"]:
            self._write(":FLD2;")
                
    def get_foldback_protection(self):
        """
        Returns FD followed by the Foldback protection status.
            FD1 - Foldback is armed
            FD0 - Foldback is released
            
        python: stored as self.foldback boolean
        """
        out = self._ask(":FLD?;")
        assert out[:2] == "FD"
        if out == "FD1":
            self.foldback_armed = True
        elif out == "FD0":
            self.foldback_armed = False
        else:
            raise ValueError
        return self.foldback_armed
        
    def set_over_voltage_protection(self,volt):
        """
        Sets the over-voltage protection level in volts. Over-voltage range settings are given in table 5-3:
        Model       MIN.    MAX.
        ZUP6-XY     0.20    7.50
        ZUP10-XY    00.5    13.0
        ZUP20-XY    01.0    24.0
        ZUP36-XY    01.8    40.0
        ZUP60-XY    03.0    66.0
        ZUP80-XY    04.0    88.0
        ZUP120-XY   006.0   132.0
        Table 5-3: Over-voltage programming range. 
        Example - ZUP10-XY :OVP08.4;
        """
        assert 0 <= volt <= self.max_voltage
        self._write(":OVP%1.2f;" % volt)
        #TODO: need to check bounds for specific model
        #TODO: this only has the correct decimal points for ZUP6



    def get_over_voltage_protection(self):
        """
        Returns the string OP followed by the present programmed 
        over-voltage protection value. 
        The over-voltage range is given in table 5-3.
        Example- OP08.4
        
        python: converts result to float
        """
    
        out = self._ask(":OVP?;")
        assert out[:2] == "OP"
        self.over_voltage = float(out[2:])
        return self.over_voltage
        
                
    def set_under_voltage_protection(self,volt):
        """
        Sets the under-voltage protection limits in volts.
        Under-voltage range settings are given in table 5-4:
        Table 5-4: Under-voltage programming range.
        
        Model       MIN.    MAX.
        ZUP6-XY     0.00    5.98
        ZUP10-XY    0.00    9.97
        ZUP20-XY    00.0    19.9
        ZUP36-XY    00.0    35.9
        ZUP60-XY    00.0    59.8
        ZUP80-XY    00.0    79.8
        ZUP120-XY   000.0   119.8

        Example - ZUP20-XY :UVP07.3;
        """
        
        assert 0 <= volt <= self.max_voltage
        self._write(":UVP%1.2f;" % volt)
        #TODO: need to check bounds for specific model
        #TODO: this only has the correct decimal points for ZUP6


    def get_under_voltage_protection(self):
        """
        Returns the string UP followed by the present programmed 
        under-voltage protection value.
        The under-voltage range is given in table 5-4.
        
        Example- UP07.3
        
        python: converts result to float
        """
    
        out = self._ask(":UVP?;")
        assert out[:2] == "UP"
        self.under_voltage = float(out[2:])
        return self.under_voltage
    
    def set_auto_restart_mode(self, ast=True):
        """
        Sets the auto-restart mode to On or Off.
        :AST1; - Auto-restart is On
        :AST0; - Auto-restart is Off
        
        python: takes a boolean ast
        """
        if ast:
            self._write(":AST1;")
        else:
            self._write(":AST0;")
        
    def get_auto_restart_mode(self):
        """
        Returns the string AS followed by the auto-restart mode status.
            AS1 - Auto-restart is ON
            AS0 - Auto-restart is Off

        python: converts result to boolean, stored in self.auto_restart_mode
        """
        out = self._ask(":AST?;")
        assert out[:2] == "AS"
        if out == "AS1":
            self.auto_restart_mode = True
        elif out == "AS0":
            self.auto_restart_mode = False
        else:
            raise ValueError
        return self.auto_restart_mode
        
    #### 5.5.4 Status control
    
    def get_operational_status(self):
        """ Use get_complete_status instead"""
        raise NotImplementedError
        #TODO
    
    def get_alarm_status(self):
        """ Use get_complete_status instead"""
        raise NotImplementedError
        #TODO
            
    def get_programming_error_status(self):
        """ Use get_complete_status instead"""
        raise NotImplementedError
        #TODO    

    def get_complete_status(self):
        """
        Reads the complete status of the power supply.
        This query returns ASCII characters representing the following data:
        AV<actual voltage >
        SV<voltage setting>
        AA<actual current>
        SA<current setting>
        OS<operational status register>
        AL<alarm status register>
        PS<programming error register>
        example:
        AV5.010SV5.010AA00.00SA24.31OS00010000AL00000PS00000
        
        python: stores all the values and returns a tuple of them
        """
        
        if not hasattr(self, '_complete_status_re_prog'):
            f_re = "([+-]?\\d*\\.\\d+)(?![-+0-9\\.])" # floating point number regex
            self.complete_status_re_prog = re.compile(
                "AV" + f_re + "SV" + f_re + "AA" + f_re + "SA" + f_re + "OS(\\d+)AL(\\d+)PS(\\d+)")


        out = self._ask(":STT?;")

        _av, _sv, _aa, _sa, _os, _al, _ps = self.complete_status_re_prog.findall(out)[0]

        self.voltage_actual = float(_av)
        self.voltage_setp   = float(_sv)
        self.current_actual = float(_aa)
        self.current_setp   = float(_sa)
        self.operational_status_register = _os
        self.alarm_status_register       = _al
        self.programming_status_register  = _ps
        
                 
        #TODO interpret status registers
        
        #operation status register
        """
        Operational Status Register:
        
        The operational status register records signals that are part of the power 
        supply's normal operation. In addition to the normal operation data, the register
        holds an alarm bit which indicates that one of the alarm (fault) register bits is
        set. The register is automatically updated and reading it does not change it's
        content. Clearing the register is done by DCL command.
        See table 5-5 for Operational Status Register content.
        
        Table 5-5: Operational status register content.
                
        Bit Name Bit No     Meaning
        cc/cv       1       '0' - Indicates constant voltage, '1' - constant current.
        fold        2       '1' - Indicates foldback protection is armed.
        ast         3       '1' - Indicates auto-restart is on, '0' - auto-restart is off.
        out         4       '1' - Indicates output is on , '0' -output is off.
        srf         5       '0' - Indicates foldback protection SRQ is disabled , '1' - enabled.
        srv         6       '0' - Indicates over voltage protection SRQ is disabled , '1' - enabled.
        srt         7       '0' - Indicates over temp. protection SRQ is disabled , '1' - enabled.
        alarm       8       '1' - Indicates that an alarm register bit is set. (note*1)
        """
        
        self.cc_cv    = bool(int(_os[0]))
        self.foldback_armed = bool(int(_os[1]))
        self.auto_restart_mode = bool(int(_os[2]))
        self.output   = bool(int(_os[3]))
        self.foldback_srq = bool(int(_os[4]))
        self.over_voltage_srq = bool(int(_os[5]))
        self.over_temp_srq = bool(int(_os[6]))
        self.alarm_active = bool(int(_os[7]))
        
        #Alarm status register
        """
        Alarm Status Register:
        
        The alarm status register records fault conditions occurring during power supply
        operation. Any set bit in this register causes the 'alarm' bit in the operational
        status register to be set. Reading the register does not change it's content.
        The register is cleared by :DCL; command.
        
        Bit Name    Bit No  Meaning
        ovp         1       '1' - Indicates that the over-voltage protection was tripped (*3)
        otp         2       '1' - Indicates that the over-temperature protection was tripped (*3)
        a/c fail    3       '1' - Indicates that a failure occurred at the input voltage supply (*1)
        fold        4       '1' - Indicates that the foldback protection was activated (*2)
        prog        5       '1' - Indicates a programming error has occurred (*3)
        """
        
        self.alarm_ovp      = bool(int(_al[0]))
        self.alarm_otp      = bool(int(_al[1]))
        self.alarm_ac_fail  = bool(int(_al[2]))        
        self.alarm_foldback = bool(int(_al[3]))
        self.alarm_prog     = bool(int(_al[4]))
        
        #Programming Error Codes Register
        """
        Error Codes Register:

        The error codes register records errors that occurred during the programming of
        the power supply. Any set bit in this register causes the 'prog' bit in the alarm
        status register to be set. Reading the register does not change it's content. The
        register is cleared by :DCL; command.
        
        Bit Name        Bit No  Meaning
        not used        1
        wrong command   2   '1' - Indicates that an unknown string was received
        buffer overflow 3   '1' - Indicates an overflow in the communication buffer
        wrong voltage   4   '1' - Indicates an attempt to program the power supply to a voltage out of specification limits.
        wrong current   5   '1' - Indicates an attempt to program the power supply to a current out of specification limits.
        """
        self.prog_err_wrong_command   = bool(int(_ps[1]))
        self.prog_err_buffer_overflow = bool(int(_ps[2]))
        self.prog_err_wrong_voltage   = bool(int(_ps[3]))
        self.prog_err_wrong_current   = bool(int(_ps[4]))
        
        
        return ( self.voltage_actual, self.voltage_setp, 
                 self.current_actual, self.current_setp,
                 self.operational_status_register,
                 self.alarm_status_register,
                 self.programming_status_register
                 )



    #### 5.7 Service Request (SRQ) -- interrupts
    
    #TODO interrupts not implemented yet


######### Format Strings for settings voltage and current
# we need these because Zup requires the correct number of digits
# depending on model
v_format_strs = {
    # key: volt max
    # value: format string {:0total_char.decimalsf}
    6: "{:05.3f}",
    10:"{:06.3f}",
    20:"{:06.3f}", 
    36:"{:05.2f}",
    60:"{:05.2f}",
    80:"{:05.2f}",
    120:"{:06.2f}"}

i_format_strs = {
    #(V,A): fmt_str {:0total_char.decimalsf}
    (6,33.0):   "{:05.2f}",
    (6,66.0):   "{:05.2f}",
    (6,132.0):  "{:06.2f}",
    
    (10,20.0):  "{:06.3f}",
    (10,40.0):  "{:05.2f}",
    (10,80.0):  "{:05.2f}",
    
    (20,10.0):  "{:06.3f}",
    (20,20.0):  "{:06.3f}",
    (20,40.0):  "{:05.2f}",
    
    (36,6.0):   "{:05.3f}",
    (36,12.0):  "{:06.3f}",
    (36,24.0):  "{:06.3f}",
    
    (60,3.5):   "{:05.3f}",
    (60,7.0):   "{:05.3f}",
    (60,14.0):  "{:06.3f}",
    
    (80,2.5):   "{:06.4f}",
    (80,5.0):   "{:05.3f}",
    
    (120,1.8):   "{:06.4f}",
    (120,3.6):   "{:05.3f}",
}

### Test case

"""
if __name__ == '__main__':
    
    #test_port = "/dev/tty.usbserial-FTVNWTWUA"
    test_port = "COM3"
    ps = LambdaZup(port=test_port, address = 1, always_send_address=True, debug=True)
    
    print ps.set_address()
    print ps.clear_comm_buffer()
    print ps.get_model()
    print ps.get_software_revision()
    print ps.get_remote_mode()

    print ps.get_complete_status()
    
    print ps.get_voltage_setp()
    print ps.get_voltage_actual()
    print ps.set_voltage(5)
    print ps.get_voltage_setp()
    print ps.get_voltage_actual()

    print ps.get_current_setp()
    print ps.get_current_actual()
    print ps.set_current(1.0)
    print ps.get_current_setp()
    print ps.get_current_actual()

    print ps.get_output()
    print ps.set_output(True)
    time.sleep(2)
    print ps.get_output()
    print ps.set_output(False)
    
    print ps.get_complete_status()
"""