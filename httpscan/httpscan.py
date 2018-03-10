""" HTTPScan - search subnet for HTTP servers that match a regular expression """

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

logger = logging.getLogger(__name__)


async def fetch_page(session, host):
    await asyncio.sleep(random.randint(0, 25) * 0.1)
    start = time.time()
    logger.info('Fetch from {}'.format(host))

    try:
        response = await session.get(host, allow_redirects=False)
    except aiohttp.ClientResponseError as err:
        # likely a 404 implying HTTP but no page
        # likely a 401 implying HTTP but no access
        # FIXME: for instance, a gateway
        # headers are available via err.headers()
        # https://multidict.readthedocs.io/en/stable/multidict.html#multidict.CIMultiDict
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

    logger.info('Recvd from {} after {:.2f}s'.format(host, time.time() - start))
    return results_tuple


async def asynchronous(urls=None, regex_filter=None):
    http_devices = {}
    qualified_devices = []
    connection = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connection, 
        conn_timeout=5, raise_for_status=True) as session:
        
        futures = [fetch_page(session, url) for url in urls]

        for future in asyncio.as_completed(futures):
            response = await future
            if 'found' in response[1]:
                http_devices[response[0]] = response[2]
                logger.debug('Processed %s', response[0])
                if regex_filter.search(response[2]):
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
        logger.error('Scan limited to 256 addresses, requested %d.', network_object.num_addresses)
        raise NotImplementedError
    elif network_object.num_addresses > 1:
        # async request upto 256 hosts
        network_hosts = network_object.hosts()
    else:
        # assume user intent was a single IP address
        network_hosts = [network_object.network_address]
    # TODO: add try for a test urlunsplit
    return (urlunsplit(('http',str(ip),path,'','')) for ip in network_hosts)


def survey(network=None, path='', pattern='', log=False):
    if log:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.CRITICAL)

    network_scan = asyncio.ensure_future(asynchronous(
        urls=url_generator(network=network, path=path),
        regex_filter=re.compile(pattern))
        )
    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(network_scan)
    # Zero-sleep to allow underlying connections to close
    # http://aiohttp.readthedocs.io/en/stable/client_advanced.html#graceful-shutdown
    ioloop.run_until_complete(asyncio.sleep(0))
    ioloop.close()
    return network_scan.result()


def cli():
    """ Command line interface """
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(
        '%(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(ch)

    import argparse
    parser = argparse.ArgumentParser(description="Search 'network' for hosts with a \
    response to 'path' that matches 'filter'")
    parser.add_argument('network', help='IP address with optional mask, e.g. 192.168.0.0/24')
    parser.add_argument('-p', '--path', help='URL path at host, e.g. index.html',
        default='')
    parser.add_argument('-f', '--filter', help='Regular expression pattern for filter',
        dest='pattern', default='')
    parser.add_argument('-l', '--log', help='Enable logging', action='store_true')
    args = parser.parse_args()
    print('Scanning, please wait ...')
    result = survey(**vars(args))
    print('Found {} match(es) for {} on {}'.format(len(result), args.pattern, args.network))
    for x in sorted(result, key=ipaddress.ip_address):
        print(x)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,                                                 \
        format='%(asctime)s.%(msecs)03d %(levelname)s:%(module)s:%(funcName)s: %(message)s', \
        datefmt="%H:%M:%S")

    # NETWORK = '216.164.167.16/28'   # kiosk
    # NETWORK = '10.161.129.0/24'     # work lan
    # NETWORK = '10.161.129.197'        # single
    NETWORK = '192.168.0.0/24'      # home lan
    result = survey(NETWORK, 
        # pattern=re.compile('(P|p)hilips'),
        log=True)
    print(sorted(result, key=ipaddress.ip_address))
