from lambda_zup import LambdaZup
from pprint import pprint

test_port = "COM3"

ps1 = LambdaZup(port=test_port, address = 1, always_send_address=True, debug=True)
ps2 = LambdaZup(port=ps1.ser,   address = 2, always_send_address=True, debug=True)


for ps in [ps1, ps2]:
    print "ps", ps.address, "="*70
    print ps.clear_comm_buffer()
    print ps.get_model()
    print ps.get_software_revision()
    print ps.get_remote_mode()
    #print ps.set_output(False)
    #print ps.set_current(1.0)
    print ps.set_voltage(5.0)
  
    print ps.set_over_voltage_protection(6.0)
    print ps.get_over_voltage_protection()
  
    print ps.get_complete_status()

    
    """
    print ps.set_foldback_protection("cancel")
    print ps.get_foldback_protection()

    print ps.set_under_voltage_protection(0.0)
    print ps.get_under_voltage_protection()

    print ps.set_over_voltage_protection(6.0)
    print ps.get_over_voltage_protection()
    """
    
    pprint(ps.__dict__)

    
print ps1.alarm_active, ps2.alarm_active