import sys
import argparse
from jnpr.junos import Device
from jnpr.junos.op.routes import RouteTable
from pprint import pprint as pp

Device.auto_probe = 5

def main():
    args = cli_run()
    find_path(args.device, args.destination)

def find_path(device, destination):
    path = []
    #print('Analyazing path from device {} to destination IP {}'.format(device, destination))

    print('Egress interface for {} is {}'.format(device, get_egress_details(device, destination)))

def get_egress_details(device, destination):
    try:
        dev = Device(host=device)
        dev.open()
        routes = RouteTable(dev)
        routes.get(destination, table='inet.0', protocol='rsvp')
        for route in routes:
            for nh in route.nh.keys():
                if route.nh[nh].selected == True:
                    return  nh
    except:
        print('Unable to connect to {}'.format(device))
        sys.exit()

def cli_run():
    parser = argparse.ArgumentParser(description='Determine network path taken based on starting device and destination IP and gather link details.')
    parser.add_argument('device', help='Device hostname/IP to start path discovery from')
    parser.add_argument('destination', help='Destomation IP address to test path to')
    args = parser.parse_args()
    return args

if '__main__' in __name__:
    main()