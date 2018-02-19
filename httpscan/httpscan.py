import time
import random
import asyncio
import aiohttp
import argparse
from concurrent.futures import FIRST_COMPLETED
import logging
import ipaddress
from urllib.parse import urlunsplit, urlsplit
import re

DEFAULT_TIMEOUT = 10

logging.basicConfig(level=logging.DEBUG,                                                 \
    format='%(asctime)s.%(msecs)03d %(levelname)s:%(module)s:%(funcName)s: %(message)s', \
    datefmt="%Y-%m-%d %H:%M:%S")


async def fetch_page(session, host):
    await asyncio.sleep(random.randint(0, 25) * 0.1)
    start = time.time()
    logging.debug('Fetch from {}'.format(host))

    try:
        response = await session.get(host, allow_redirects=False)
    except aiohttp.ClientResponseError as err:
        # likely a 404 implying HTTP but no page
        results_tuple = (host, 'no page', err)
    except aiohttp.ClientConnectorError as err:
        # likely device at IP but no HTTP server
        results_tuple = (host, 'no http', err)
    except aiohttp.ServerConnectionError as err:
        # likely ServerTimeoutError implying no device at IP
        results_tuple = (host, 'no dev', err)
    except aiohttp.InvalidURL as err:
        # likely a malformed URL
        results_tuple = (host, 'no URL', err)
    # except aiohttp.ClientOSError as err:
    #     # TODO: source?
    #     results_tuple = (host, 'unknown', err)
    # except Exception as err:
    #     # TODO: source?
    #     results_tuple = (host, 'unknown', err)
    else:
        try:
            text_response = await response.text()
        except aiohttp.ClientPayloadError as err:
            # trouble reading page TODO: anyway to recover?
            results_tuple = (host, 'no read', err)
        else:
            results_tuple = (host, 'found', text_response) # TODO: add response.headers?
        response.close()

    logging.debug('Recvd from {} after {:.2f}s'.format(host, time.time() - start))
    return results_tuple


async def asynchronous(urls=None, filter=None):
    http_devices = {}
    qualified_devices = []
    connection = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connection, 
        conn_timeout=10, raise_for_status=True) as session:
        
        futures = [fetch_page(session, url) for url in urls]

        for future in asyncio.as_completed(futures):
            response = await future
            if 'found' in response[1]:
                http_devices[response[0]] = response[2]
                logging.debug('Processed %s', response[0])
                if filter.search(response[2]):
                    qualified_devices.append(urlsplit(response[0]).netloc)

    # print('The following responded to HTTP:')
    # for x in http_devices.keys():
    #     print(x)

    # print('The following passed the filter:')
    # qualified_devices.sort()
    # for x in qualified_devices:
    #     print(x)

    return qualified_devices


def url_generator(network=None, path=''):
    # TODO: add try
    network_object = ipaddress.ip_network(network)
    if network_object.num_addresses > 256:
        # will need to batch process this case otherwise we run out of selectors
        logging.error('Scan limited to 256 addresses, requested %d.', network_object.num_addresses)
        raise NotImplementedError
    elif network_object.num_addresses > 1:
        # async request upto 256 hosts
        network_hosts = network_object.hosts()
    else:
        # assume user intent was a single IP address
        network_hosts = [network_object.network_address]
    # TODO: add try for a test urlunsplit
    return (urlunsplit(('http',str(ip),path,'','')) for ip in network_hosts)


def survey(network=None, path='', filter='', log=True):
    # FIXME: filter='' doesnt return gateway
    # TODO: parameter order?
    # TODO: remove log parameter
    network_scan = asyncio.ensure_future(asynchronous(
        urls=url_generator(network=network, path=path),
        filter=re.compile(filter))
        )
    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(network_scan)
    # Zero-sleep to allow underlying connections to close
    # http://aiohttp.readthedocs.io/en/stable/client_advanced.html#graceful-shutdown
    ioloop.run_until_complete(asyncio.sleep(0))
    ioloop.close()
    return network_scan.result()


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Search 'network' for hosts with a \
    response to 'path' that matches 'filter'")
    parser.add_argument('network', help='IP address with optional mask, e.g. 192.168.0.0/24')
    parser.add_argument('-p', '--path', help='URL path at host, e.g. index.html',
        default='')
    # TODO: handle special characters for re's other than quoting?
    parser.add_argument('-f', '--filter', help='Filter in regular expression syntax',
        default='')
    parser.add_argument('-l', '--log', help='Enable logging', action='store_true')
    args = parser.parse_args()
    if not args.log:
        logging.disable(logging.CRITICAL)
    logging.debug('%s', args)
    print('Scanning, please wait ...')
    # TODO: this also forces the log parameter into survey()
    result = survey(**vars(args))
    print('Found {} match(es) for {} on {}'.format(len(result), args.filter, args.network))
    result.sort()   # FIXME: fix sort
    for x in result:
        print(x)


if __name__ == '__main__':
    # NETWORK = '216.164.167.16/28'   # kiosk
    # NETWORK = '10.161.129.0/24'     # work lan
    # NETWORK = '10.161.129.197'        # single
    NETWORK = '192.168.0.0/24'      # home lan
    # filter=re.compile('(P|p)hilips'))
    # result = survey(NETWORK)
    # print(result)
    cli()
