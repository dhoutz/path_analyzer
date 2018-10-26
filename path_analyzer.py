#!/usr/bin/python

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
    hop  = 0
    results = {}
    current_device = device
    destination = destination + '/32'
    last_hop = False
    # Hard coded for now until we detect device being final hop
    while last_hop == False:
        print 'Processing device {} as hop {}'.format(current_device, hop)
        dev = Device(host=current_device)
        dev.open()
        if hop != 0:
            ingress_details = get_ingress_details(dev, device)
        egress_details = get_egress_details(dev, current_device, destination)
        dev.close()
        if egress_details == None:
            last_hop = True
        results[hop] = {current_device: egress_details}
        if last_hop != True:
            current_device = egress_details['next_device']
        hop = hop + 1
        print '\n\n'
        
    print '\n\n********** PATH RESULTS ***********\n\n'
    pp(results)

def get_egress_details(dev, device, destination):
    #try:
    print 'Finding path to {} from {}'.format(destination, device)
    egress_interfaces = []
    #dev = Device(host=device)
    #dev.open()
    routes = RouteTable(dev)
    routes.get(destination, table='inet.0')
    for route in routes:
        for nexthop in route.nh:
            if nexthop.selected == True:
                print ' Found egress interface {} on {}'.format(nexthop.key, device)
                if 'ae' in nexthop.key:
                    interfaces =  get_lag_members(dev, nexthop.key) 
                    for i in interfaces:
                        egress_interfaces.append(i)
                elif nexthop.key == 'lo0.0':
                    egress_interfaces = None
                    print 'Last hop!'
                else:
                    egress_interfaces.append(nexthop.key)
                break
    print 'Egress interface(s) on {} is {}'.format(device, egress_interfaces)
    if egress_interfaces != None:
        remote_device_details, next_device  = get_remote_device(dev, egress_interfaces)
        next_device = fix_hostname(remote_device_details[0][egress_interfaces[0]]['remote_device'])
        return {'next_device': next_device, 'egress_interfaces': remote_device_details}
    else:
        return None

    #except:
    #    print('Unable to connect to {}'.format(device))
    #    sys.exit()

def get_ingress_details(dev, device):
    print 'Grabbbing ingress details from {}'.format(device)
    pass

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
    return egress_interfaces, iface.remote_sysname

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
    if hostname.startswith('re'):
        hostname = hostname[4:]
        return hostname
    else:
        return hostname
    

def cli_run():
    parser = argparse.ArgumentParser(description='Determine network path taken based on starting device and destination IP and gather link details.')
    parser.add_argument('device', help='Device hostname/IP to start path discovery from')
    parser.add_argument('destination', help='Destomation IP address to test path to')
    args = parser.parse_args()
    return args

if '__main__' in __name__:
    main()
