from ScopeFoundry.hardware import HardwareComponent
from .lambda_zup import LambdaZup
import time

class LambdaZupHW(HardwareComponent):
    
    name = 'lambda_zup'
    
    def setup(self):
        S = self.settings
        S.New('port', dtype=str,  initial='COM1')
        S.New('always_send_address', dtype=bool, initial=True)
        S.New('address', dtype=int, initial=1)
        
        S.New('model', dtype=str, ro=True)
        
        S.New('current_actual', dtype=float, unit='A', ro=True)
        S.New('current_setpoint', dtype=float, unit='A', ro=False, spinbox_decimals=3)

        S.New('voltage_actual', dtype=float, unit='V', ro=True)
        S.New('voltage_setpoint', dtype=float, unit='V', ro=False)
        
        S.New('output_enable', dtype=bool)
        
        S.New('live_update', dtype=bool, initial=False)
        
        
    def connect(self):
        S = self.settings
        self.dev = LambdaZup(port=S['port'],
                             address=S['address'],
                             always_send_address = S['always_send_address'],
                             debug=S['debug_mode'])
        
        S['model'] = self.dev.get_model()
        
        S.current_actual.connect_to_hardware(
            read_func = self.dev.get_current_actual
            )
        
        S.current_setpoint.connect_to_hardware(
            read_func  = self.dev.get_current_setp,
            write_func = self.dev.set_current)
        
        S.voltage_actual.connect_to_hardware(
            read_func = self.dev.get_voltage_actual
            )
        
        S.voltage_setpoint.connect_to_hardware(
            read_func  = self.dev.get_voltage_setp,
            write_func = self.dev.set_voltage)
        
        S.output_enable.connect_to_hardware(
            read_func  = self.dev.get_output,
            write_func = self.dev.set_output)
        
        self.read_from_hardware()
        
    def disconnect(self):
        self.settings.disconnect_all_from_hardware()
        
        if hasattr(self, 'dev'):
            self.dev.close()
            del self.dev
            
    def threaded_update(self):
        if self.settings['live_update']:
            try:
                self.settings.current_actual.read_from_hardware()
                self.settings.voltage_actual.read_from_hardware()
            except Exception as err:
                print(err)
            time.sleep(0.5)        