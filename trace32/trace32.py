"""
Trace32 Lauterbach Library

This library is part of ITest framework.

@author:  Jarold Gonzalez
@version: 1.0.0

@change:  JGonzalez - 1.0.0 - Integration test report hith hyperlinks
"""

# -------------------- [IMPORTS FILES] ----------------------------------------

from ctypes import CDLL
import sys
import os
import array
import time
import re
import subprocess

# Trace32 emulator state
T32_STATE_DOWN = 0
T32_STATE_HALTED = 1
T32_STATE_STOPPED = 2
T32_STATE_RUNNING = 3

# Breakpoint wait timeout
BREAKPOINT_TIMEOUT = 6.0

# -------------------- [CONSTANT DEFINITIONS] ---------------------------------

class T32Legacy(object):

    def __init__(self, port_c1='20000'):
        pass

class T32DebuggerDll (object):

    def __init__(self, port_c1='20000'):
        """ Constructor. Loads t32lib.dll library and establishes connection with TRACE32. """
        try:
            self.t32lib = CDLL('t32api64.dll')
        except WindowsError:
            print("[ERROR] Failed to load t64api.dll\n")
            print("[ERROR] Are you using python 64bit installation?")
            sys.exit()

        if not self._initialize_connection(port_c1):
            print("[ERROR] Connection with Trace32 failed.")
            sys.exit()
        self.cmd('var.delwatch')

    def _initialize_connection(self, port_c1):
        if self._init_trace32() != 0:
            print("[ERROR] Failed to initialize connection with Trace32.")
            return False

        if self.attach() != 0:
            print("[ERROR] Connection with Trace32 in attach() function, trying again...")
            self.t32lib.T32_Exit()
            if self._init_trace32() != 0 or self.attach() != 0:
                print("[ERROR] Connection with Trace32 failed after retry.")
                return False

        return True

    def _init_trace32(self):
        """ Initialize the driver and TRACE32 connection. @return: 0 if initialization was successful. """
        if self.t32lib.T32_Init() != 0:
            print("Failed to initialize connection with Trace32.")
            return False
        return True

    def attach(self):
        """ Attach to the running TRACE32 instance. @return: 0 if attach was successful. """
        return self.cmd('Sys.Mode Attach')
    
    def cmd(self, string):
        """ This function send a command to Trace32. @return: 0 if it was successful. """
        return self.t32lib.T32_Cmd(str.encode(string))

    def exit(self):
        """ This function close t32 """
        self.cmd('Quit')

    def reset_runtime(self):
        ''' Reset the runtime window inside T32 '''
        self.cmd('RunTime.RESet')

    def get_runtime_meas(self):
        ''' Return the time between two breakpoints '''
        self.cmd('PRINT RunTime.ACTUAL()')
        meas = self.get_message()
        return meas
    
    def get_message(self):
        """
        Most PRACTICE commands write messages to the message line and AREA window of TRACE32. This
        function reads the contents of the message line and the type of the message.

        @return: 0 for OK, otherwise Error value
        """
        str1 = create_string_buffer(4096)
        mode = c_byte()
        self.t32lib.T32_GetMessage(str1, byref(mode))
        str2=str1.value
        retstr=str2.decode('utf-8')
        return retstr

    def get_cmd_state(self):
        """
        Returns the run-state of PRACTICE. Use this command to poll for the end of a PRACTICE script started via
        T32_Cmd().

        @return: 0 for OK, otherwise Error value
        """
        result = c_int()
        self.t32lib.T32_GetPracticeState(byref(result))
        return result.value


class T32(object):
    import lauterbach.trace32.rcl as t32



    def reset_cpu(self):
        """
        Tries to reset the target CPU. This is done by executing the PRACTICE commands SYStem.UP and
        Register.RESet. This function can also be used to get control after the target software has crashed.

        @return: 0 for OK, otherwise Error value
        """
        return self.t32lib.T32_ResetCPU()

    def read_memory(self, address, size):
        """
        Reads data from target memory. The size of the data block is not limited

        @return: list in bytes of the memory content
        """
        add = c_ulong(address)
        acc = c_int(0x00)
        buf = create_string_buffer(size)
        siz = c_int(size)
        self.t32lib.T32_ReadMemory(add, acc, buf, siz)
        s = array.array('B')
        s.frombytes(buf.raw)
        return s.tolist()

    def write_memory(self, address, data):
        """
        Writes data to target memory. The size of the data block is not limited.
        This function should be used to access variables and make other not time
        critical memory writes.

        @return: 0 for OK, otherwise Error value
        """
        add = c_ulong(address)
        acc = c_int(0x00)
        buf = array.array('B', data)
        siz = c_int(len(data))
        return self.t32lib.T32_WriteMemory(add, acc, buf.tobytes(), siz)

    def read_pp(self):
        """
        This function reads the current value of the program pointer. It is only valid if the application is
        stopped, i.e. the state of the ICE is "Emulation stopped" (see T32_GetState). The program pointer is
        a logical pointer to the address of the next executed assembler line. Unlike T32_ReadRegister, this
        function is completely processor independent.

        @return: Program Pointer (PP) value.
         """
        pp = c_ulong()
        self.t32lib.T32_ReadPP(byref(pp))
        return pp.value

    def set_breakpoint_at_address(self, address, btype=''):
        """
        Description: Sets a breakpoint in the passed address.

        @param address: Address to set the breakpoint
        @param btype:   Breakpoint types
                        - if omitted, the breakpoint will be a normal 'execution' breakpoint
                        - 'R' or 'r' is used for 'read' breakpoint
                        - 'W' or 'w' is used for 'write' breakpoint

        @return: 0 for OK, otherwise Error value
        """
        add = c_ulong(address)
        if btype == 'R' or btype == 'r':
            brk = c_int(0x0008)
            acc = c_int(0x00)
        elif btype == 'W' or btype == 'w':
            brk = c_int(0x0010)
            acc = c_int(0x00)
        else:
            brk = c_int(0x0001)
            acc = c_int(0x01)
        siz = c_int(1)
        return self.t32lib.T32_WriteBreakpoint(add, acc, brk, siz)

    def set_breakpoint_at_var(self, symbol, btype):
        """
        Description: Sets a breakpoint in a given variable, global or static.
        @param symbol: Variable name
        @param btype:  Can be "R" for read or "W" for write breakpoint
        """
        self.set_breakpoint_at_address(self.get_symbol_address(symbol), btype)

    def set_breakpoint_at_function(self, text):
        """
        Set breakpoint at the function

        @param text: Function name
        """
        self.cmd('break.s ' + str(text) + ' /Onchip')

    def clear_breakpoint_at_function(self, text):
        """
        Clear breakpoint at function
        @param text: Function name
        """
        self.cmd('break.dis ' + str(text))

    def set_breakpoint_after_text(self, filename, tag):
        """
        Set breakpoint inside the C file in the line after the specified tag

        @param filename: Absolute path of the file name
        @param tag: Tag used to identify the line

        Examples:
            C file pwmo_test.c is:
                ...
            87   if (Cnt == 1) {     /* iTEST_BP_1 */
            88       Cnt--;
            89       for (test_1 = 0; test_1 < PWMO_TOTAL_CHANNELS; test_1++) {
            90       HW_InitPWM(&indepPWM[test_1], HW_LOGIC_HIGH_DRIVEN);
            91   }
            92   etpu_test_pwmo.DeadTime = 3.0f;
            93   etpu_test_pwmo.DutyU = 0.80;
                ...

            c_files = {'pwmo_test.c' : 'C:/JGonzalezsosa/06_Software/source/test/pwmo_test.c', ...}
            t32 = T32()
            t32.set_breakpoint_after_text('c_files['pwmo_test.c'], 'iTEST_BP_1 ') # Will place a breakpoint in line 88
        """
        f = open(filename, 'r')
        line = 0
        for codeline in f.readlines():
            line = line + 1
            if tag in codeline:
                break

        matchObj = re.findall(r'\w*\.c', filename)
        symbol = '\\' + matchObj[0].replace('.c', '') + '\\' + str(line + 1)
        self.set_breakpoint_at_address(self.get_symbol_address(symbol))

    def set_breakpoint_at_text(self, filename, tag):
        """
        Set breakpoint inside the C file in line of the specified tag

        @param filename: Absolute path of the file name
        @param tag: Tag used to identify the line

        Examples:
            C file pwmo_test.c is:
                ...
            87   if (Cnt == 1) {     /* iTEST_BP_1 */
            88       Cnt--;
            89       for (test_1 = 0; test_1 < PWMO_TOTAL_CHANNELS; test_1++) {
            90       HW_InitPWM(&indepPWM[test_1], HW_LOGIC_HIGH_DRIVEN);
            91   }
            92   etpu_test_pwmo.DeadTime = 3.0f;
            93   etpu_test_pwmo.DutyU = 0.80;
                ...

            c_files = {'pwmo_test.c' : 'C:/JGonzalezsosa/06_Software/source/test/pwmo_test.c', ...}
            t32 = T32()
            t32.set_breakpoint_at_text('c_files['pwmo_test.c'], 'iTEST_BP_1 ') # Will place a breakpoint in line 87
        """
        f = open(filename, 'r')
        line = 0
        for codeline in f.readlines():
            line = line + 1
            if tag in codeline:
                break

        matchObj = re.findall(r'\w*\.c', filename)
        symbol = '\\' + matchObj[0].replace('.c', '') + '\\' + str(line)
        self.set_breakpoint_at_address(self.get_symbol_address(symbol))

    def clear_breakpoint_at_address(self, address, btype=''):
        """
        Clears breakpoint at a specified address.
        @param address: breakpoint address
        @param btype: breakpoint type
        @return: 0 if OK.
        """
        add = c_ulong(address)
        if btype == 'R' or btype == 'r':
            brk = c_int(0x0108)
            acc = c_int(0x00)
        elif btype == 'W' or btype == 'w':
            brk = c_int(0x0110)
            acc = c_int(0x00)
        else:
            brk = c_int(0x0101)
            acc = c_int(0x01)
        siz = c_int(1)
        return self.t32lib.T32_WriteBreakpoint(add, acc, brk, siz)

    def clear_breakpoint_after_text(self, filename, tag):
        """
        Remove breakpoint inside the C file from the line below of the specified tag

        @param filename: Absolute path of the file name
        @param tag: Tag used to identify the line

        Examples:
            C file pwmo_test.c is:
                ...
            87   if (Cnt == 1) {     /* iTEST_BP_1 */
            88       Cnt--;
            89       for (test_1 = 0; test_1 < PWMO_TOTAL_CHANNELS; test_1++) {
            90       HW_InitPWM(&indepPWM[test_1], HW_LOGIC_HIGH_DRIVEN);
            91   }
            92   etpu_test_pwmo.DeadTime = 3.0f;
            93   etpu_test_pwmo.DutyU = 0.80;
                ...

            c_files = {'pwmo_test.c' : 'C:/JGonzalezsosa/06_Software/source/test/pwmo_test.c', ...}
            t32 = T32()
            t32.clear_breakpoint_after_text('c_files['pwmo_test.c'], 'iTEST_BP_1 ') # Will place a breakpoint in line 88
        """

        f = open(filename, 'r')
        line = 0
        for codeline in f.readlines():
            line = line + 1
            if tag in codeline:
                break

        matchObj = re.findall(r'\w*\.c', filename)
        symbol = '\\' + matchObj[0].replace('.c', '') + '\\' + str(line + 1)
        self.clear_breakpoint_at_address(self.get_symbol_address(symbol))

    def clear_exec_breakpoint_at_text(self, filename, tag):
        """
        Remove breakpoint inside the C file from the specified tag

        @param filename: Absolute path of the file name
        @param text: Tag used to identify the line

        Examples:
            C file pwmo_test.c is:
                ...
            87   if (Cnt == 1) {     /* iTEST_BP_1 */
            88       Cnt--;
            89       for (test_1 = 0; test_1 < PWMO_TOTAL_CHANNELS; test_1++) {
            90       HW_InitPWM(&indepPWM[test_1], HW_LOGIC_HIGH_DRIVEN);
            91   }
            92   etpu_test_pwmo.DeadTime = 3.0f;
            93   etpu_test_pwmo.DutyU = 0.80;
                ...

            c_files = {'pwmo_test.c' : 'C:/JGonzalezsosa/06_Software/source/test/pwmo_test.c', ...}
            t32 = T32()
            t32.clear_breakpoint_after_text('c_files['pwmo_test.c'], 'iTEST_BP_1 ') # Will place a breakpoint in line 87
        """
        f = open(filename, 'r')
        line = 0
        for codeline in f.readlines():
            line = line + 1
            if tag in codeline:
                break

        matchObj = re.findall(r'\w*\.c', filename)
        symbol = '\\' + matchObj[0].replace('.c', '') + '\\' + str(line)
        self.clear_breakpoint_at_address(self.get_symbol_address(symbol))

    def clear_all_breakpoints(self):
        """
        Clears all breakpoints previously set
        """
        self.cmd('break.dis /ALL')

    def clear_var_breakpoint(self, symbol, btype):
        """
        Clear breakpoint in the specified variable

        @param symbol: Variable name
        @param btype: type of breakpoint
        """
        self.clear_breakpoint_at_address(
            self.get_symbol_address(symbol), btype)

    def go(self):
        """
        Start target (or start realtime emulation). The function will return immediately after the emulation has been
        started. The T32_GetState function can be used to wait for the next breakpoint. All other commands are
        allowed while the emulation is running

        @return: 0 if OK.
        """
        time.sleep(0.5)
        return self.t32lib.T32_Go()

    def stop(self):
        """
        Stops Trace32.

        @return: 0 if OK.
        """
        return self.t32lib.T32_Break()

    def step(self):
        """
        Executes one single step.

        @return: 0 if OK.
        """
        return self.t32lib.T32_Step()

    def get_address_at_text(self, filename, text):
        """
        Will return the address of the tag inside the specified C file

        @param filename: Absolute path of the file name
        @param text: Tag used to identify the line

        Examples:
            C file pwmo_test.c is:
                ...
            87   if (Cnt == 1) {     /* iTEST_BP_1 */
            88       Cnt--;
            89       for (test_1 = 0; test_1 < PWMO_TOTAL_CHANNELS; test_1++) {
            90       HW_InitPWM(&indepPWM[test_1], HW_LOGIC_HIGH_DRIVEN);
            91   }
            92   etpu_test_pwmo.DeadTime = 3.0f;
            93   etpu_test_pwmo.DutyU = 0.80;
                ...

            c_files = {'pwmo_test.c' : 'C:/JGonzalezsosa/06_Software/pwmo_test.c', ...}
            t32 = T32()
            reached = t32.set_breakpoint_at_text(c_files['pwmo_test.c'], 'iTEST_BP_1') # Will place a breakpoint in line 87
            if reached:
                bk_addr = t32.get_address_at_text(c_files['pwmo_test.c'], 'iTEST_BP_1')
        """
        f = open(filename, 'r')
        line = 0
        for codeline in f.readlines():
            line = line + 1
            if text in codeline:
                break

        matchObj = re.findall(r'\w*\.c', filename)
        symbol = '\\' + matchObj[0].replace('.c', '') + '\\' + str(line)
        return self.get_symbol_address(symbol)

    def get_address_after_text(self, filename, text):
        """
        Will return the address of the tag inside the specified C file

        @param filename: Absolute path of the file name
        @param text: Tag used to identify the line

        Examples:
            C file pwmo_test.c is:
                ...
            87   if (Cnt == 1) {     /* iTEST_BP_1 */
            88       Cnt--;
            89       for (test_1 = 0; test_1 < PWMO_TOTAL_CHANNELS; test_1++) {
            90       HW_InitPWM(&indepPWM[test_1], HW_LOGIC_HIGH_DRIVEN);
            91   }
            92   etpu_test_pwmo.DeadTime = 3.0f;
            93   etpu_test_pwmo.DutyU = 0.80;
                ...

            c_files = {'pwmo_test.c' : 'C:/JGonzalezsosa/06_Software/pwmo_test.c', ...}
            t32 = T32()
            reached = t32.set_breakpoint_at_text(c_files['pwmo_test.c'], 'iTEST_BP_1') # Will place a breakpoint in line 87
            if reached:
                bk_addr = t32.get_address_after_text(c_files['pwmo_test.c'], 'iTEST_BP_1')
        """

        f = open(filename, 'r')
        line = 0
        for codeline in f.readlines():
            line = line + 1
            if text in codeline:
                break

        matchObj = re.findall(r'\w*\.c', filename)
        symbol = '\\' + matchObj[0].replace('.c', '') + '\\' + str(line + 1)
        return self.get_symbol_address(symbol)

    def get_symbol_address(self, string):
        """
        Return the symbol address value

        @param string: variable or file\line

        Examples:
            t32 = T32()
            t32.get_symbol_address('PWM_Variable') # address of variable
            t32.get_symbol_address(r'\pwmo.c\87') # address of pwmo.c file, line 87
        """
        sym = c_char_p(str.encode(string))
        add = c_ulong()
        siz = c_ulong()
        acc = c_ulong()
        self.t32lib.T32_GetSymbol(sym, byref(add), byref(siz), byref(acc))
        return add.value

    def get_symbol_size(self, string):
        """
        Returns size of symbol
        @param string: variable or file\line
        """
        sym = c_char_p(str.encode(string))
        add = c_ulong()
        siz = c_ulong()
        acc = c_ulong()
        self.t32lib.T32_GetSymbol(sym, byref(add), byref(siz), byref(acc))
        return siz.value

    def read_var(self, var):
        """
        This function will read the variable

        @return: list containing variable value
        """
        var = str(var)
        if var not in self.vars_list:
            self.vars_list.append(var)
            self.cmd('var.addwatch ' + var)
        self.cmd('V ' + var)
        variable = self.get_message()

        lst = list()
        matches = re.finditer(
            r"=(\s)([a-zA-Z0-9_.-]*)", variable, re.MULTILINE)

        for matchNum, match in enumerate(matches):
            if match.group(2) != '':
                lst.append(match.group(2))
        return lst

    def read_variable(self, string):
        sym = c_char_p(str.encode(string))
        value = c_ulong()
        hvalue = c_ulong()
        self.t32lib.T32_GetSymbol(sym, byref(value), byref(hvalue))
        return value.value

    def write_var(self, var, value):
        """
        Change variable to the specified value

        @param var: variable to change the value
        @param value: value to set the variable

        @warning: Please take into account that in order to write in a variable the you have to be inside of the
                  function if is a local variable.
        """
        var = str(var)
        if var not in self.vars_list:
            self.vars_list.append(var)
            self.cmd('var.addwatch ' + var)
        self.cmd('V ' + var + ' = ' + str(value))

    def write_per_register(self,addr,datatype,value):
        """
        @param addr: Address of register(hex value) as string
        @param datatype: enter register data type among Byte,Word and Long as string
        @param value: value to be written to register. enter hex value
        """
        addr=str(addr)
        datatype=str(datatype)
        value=str(value)
        command='PER.Set.simple ANC:'+addr+ ' %'+ datatype+ ' '+value
        self.cmd(command)

    def wait_for_breakpoint(self, timeout=BREAKPOINT_TIMEOUT):
        """
        Will wait until the breakpoint is reached or timeout expires

        @param timeout: timeout in which the timer will expire
        @return: TRUE if breakpoint reached or FALSE if timeout expires
        """
        start_time = time.time()
        elapsed_time = 0.0
        while self.get_state() == T32_STATE_RUNNING and elapsed_time < timeout:
            elapsed_time = time.time() - start_time
        if elapsed_time >= timeout:
            return False
        else:
            return True
    def flash_one_ONE(self):
        self.cmd('do ./flash/FlashNotQuestions')
        a=10
        #verifying if it code successfully flashed
        while(a!=0):
            status=self.get_message()
            result1=status.find('Successfully')
            result2=status.find('flashed')
            if(result1!=-1 and result2!=-1):
                a=0
                return True
            a=a-1
        return False


    def load_symb(self):
        self.cmd('do ./operations/load_symbols')
        a=10
        #verifying if symbols are loaded successfully
        while(a!=0):
            status=self.get_message()
            result1=status.find('loaded')
            result2=status.find('successfully')
            if(result1!=-1 and result2!=-1):
                a=0
                return True
            a=a-1
        return False
    def mode(self,a):
        if a=='StandBy':
            self.cmd('SYStem.Mode StandBy')
        elif a=='Down':
            self.cmd('SYStem.Mode Down')
        elif a=='Up':
            self.cmd('SYStem.Mode Up')
        elif a=='NoDebug':
            self.cmd('SYStem.Mode NoDebug')
        elif a=='Go':
            self.cmd('SYStem.Mode Go')
        elif a=='Attach':
            self.cmd('SYStem.Mode Attach')


    def Option(self,a,selectpin):
        if a=='ResetDetection':
            if selectpin=='RESETPIN':
                self.cmd('SYStem.Option.ResetDetection RESETPIN')
            elif selectpin=='RSTINOUT':
                self.cmd('SYStem.Option.ResetDetection RSTINOUT')
            elif selectpin=='OFF':
                self.cmd('SYStem.Option.ResetDetection OFF')


    def close_T32(self):
        self.cmd('QUIT')


if __name__ == "__main__":
    ''' If the script is executed, it will run the report and validate the library '''

    dbg = t32.connect(node='localhost', port=20000, protocol="TCP", timeout=10.0)

    print (dbg)

