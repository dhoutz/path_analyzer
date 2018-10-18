import sys
import argparse
from jnpr.junos import Device
from jnpr.junos.op.lacp import LacpPortTable
from jnpr.junos.factory.factory_loader import FactoryLoader
import yaml
from pprint import pprint as pp

Device.auto_probe = 5

RouteYamlTable = \
"""
RouteTable:
 rpc: get-route-information
 args_key: destination
 item: route-table/rt
 key: rt-destination
 view: RouteTableView

RouteTableView:
 groups:
   entry: rt-entry
 fields_entry:
   protocol: protocol-name
   age: { age/@seconds : int }
 fields:
   nh: _nhTable

_nhTable:
 item: rt-entry/nh
 key: via | nh-local-interface
 view: _nhView

_nhView:
 fields:
   nexthop: to
   selected: { selected-next-hop: flag }
"""
globals().update(FactoryLoader().load(yaml.load(RouteYamlTable)))

LLDPInterfaceYamlTable = \
"""
---
LLDPInterfaceTable:
 rpc: get-lldp-interface-neighbors
 args_key: interface_device
 item: lldp-neighbor-information | lldp-local-port-id
 key: lldp-local-interface
 view: LLDPNeighborView
LLDPNeighborView:
 fields:
   local_int: lldp-local-interface | lldp-local-port-id
   local_parent: lldp-local-parent-interface-name
   remote_type: lldp-remote-chassis-id-subtype
   remote_chassis_id: lldp-remote-chassis-id
   remote_port_desc: lldp-remote-port-description
   remote_port_id: lldp-remote-port-id
   remote_sysname: lldp-remote-system-name
   remote_port_id: lldp-remote-port-id
"""
globals().update(FactoryLoader().load(yaml.load(LLDPInterfaceYamlTable)))

'''
LACPInterfaceYamlTable = \
"""
---
LACPInterfaceTable:
"""
globals().update(FactoryLoader().load(yaml.load(LACPInterfaceYamlTable)))
'''

def main():
    args = cli_run()
    find_path(args.device, args.destination)

def find_path(device, destination):
    path = []
    results = {'hop 0': get_egress_details(device, destination)}
    print '\n\n********** FINAL RESULTS ***********\n\n'
    pp(results)

def get_egress_details(device, destination):
    #try:
    print 'Finding path to {} from {}'.format(destination, device)
    egress_interfaces = []
    dev = Device(host=device)
    dev.open()
    routes = RouteTable(dev)
    routes.get(destination, table='inet.0', protocol='rsvp')
    for route in routes:
        for nh in route.nh.keys():
            if route.nh[nh].selected == True:
                print ' Found egress interface {} on {}'.format(nh, device)
                if 'ae' in nh:
                    for i in get_lag_members(dev, nh):
                        egress_interfaces.append(i)
                else:
                    egress_interfaces.append(nh)
    print 'Egress interface(s) on {} is {}'.format(device, egress_interfaces)
    remote_device_details = get_remote_device(dev, egress_interfaces)
    return {'device': device, 'egress_interfaces': remote_device_details }

    #except:
    #    print('Unable to connect to {}'.format(device))
    #    sys.exit()

def get_remote_device(dev, interfaces):
    egress_interfaces = []
    lldp_data = LLDPInterfaceTable(dev)
    for i in interfaces:
        lldp_data.get(interface_device = i)
        for iface in lldp_data:
            #print interfaces
            #print iface.key
            if iface.key in interfaces:
                print '{} is a member of {} and is connected to {}:{}'.format(iface.key, iface.local_parent, iface.remote_sysname, iface.remote_port_id)
                egress_interfaces.append({i: {'parent_interface': iface.local_parent, 'remote_device': iface.remote_sysname, 'remote_interface': iface.remote_port_id}})
    return egress_interfaces

def get_lag_members(dev, interface):
    interfaces = []
    print '  Finding LAG members for', interface
    interface = interface.split('.')[0]
    lacp_data = LacpPortTable(dev)
    lacp_data.get(interface_name=interface)
    for i in lacp_data[interface]['proto'].keys():
        print '   Found LAG member {}'.format(i)
        interfaces.append(i)
    return interfaces

def fix_hostname(hostname):
    pass


def cli_run():
    parser = argparse.ArgumentParser(description='Determine network path taken based on starting device and destination IP and gather link details.')
    parser.add_argument('device', help='Device hostname/IP to start path discovery from')
    parser.add_argument('destination', help='Destomation IP address to test path to')
    args = parser.parse_args()
    return args

if '__main__' in __name__:
    main()