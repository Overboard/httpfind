""" HTTPFind - search subnet for HTTP servers that match a regular expression """

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
    """ Perform the page fetch from an individual host.

    `session` - An aiohttp 
    [client session](http://aiohttp.readthedocs.io/en/stable/client_reference.html#client-session)  
    `host` - URL to fetch

    `return` tuple with the following:
        * The host parameter
        * A vague status string
        * Text response or an exception depending on status above
    """
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
    # except Exception as err:
    #     # Generic trap for debug
    #     results_tuple = (host, 'unknown', err)
    else:
        try:
            text_response = await response.text()
        except aiohttp.ClientPayloadError as err:
            # trouble reading page TODO: anyway to recover?
            results_tuple = (host, 'no read', err)
        else:
            results_tuple = (host, 'found', text_response)
        response.close()

    logger.info('Recvd from {} after {:.2f}s'.format(host, time.time() - start))
    return results_tuple


async def asynchronous(urls=None, re_filter=None):
    """ Asynchronous request manager for session.  Returns list of responses that
    match the filter.

    `urls` - tuple of URLs to request  
    `re_filter` - a compiled regular expression
    [object](https://docs.python.org/3/library/re.html#re-objects)
    """
    class _URLBase(str):
        """ Convenient access to hostname (ip) portion of the URL """
        @property
        def hostname(self):
            return urlsplit(self).hostname

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
                if re_filter.search(response[2]):
                    qualified_devices.append(_URLBase(response[0]))

    # print('The following responded to HTTP:')
    # for x in http_devices.keys():
    #     print(x)

    return qualified_devices


def url_generator(network=None, path=''):
    """ Return a tuple of URLs with path, one for each host on network

    `network` - IP address and subnet mask compatible with 
    [ipaddress library](https://docs.python.org/3/library/ipaddress.html#ipaddress.ip_network)  
    `path` - Path portion of a URL as defined by 
    [url(un)split](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlsplit)  
    """
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
    return (urlunsplit(('http',str(ip),path,'','')) for ip in network_hosts)


def survey(network=None, path='', pattern='', log=False):
    """ Search network for hosts with a response to path that matches pattern

    `network` - IP address and subnet mask compatible with 
    [ipaddress library](https://docs.python.org/3/library/ipaddress.html#ipaddress.ip_network)  
    `path` - Path portion of a URL as defined by 
    [url(un)split](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlsplit)  
    `pattern` - A regular expression pattern compatible with
    [re.compile](https://docs.python.org/3/library/re.html#re.compile)  
    `log` -  boolean to control logging level
    """
    if log:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.CRITICAL)

    network_scan = asyncio.ensure_future(asynchronous(
        urls=url_generator(network=network, path=path),
        re_filter=re.compile(pattern))
        )
    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(network_scan)
    # Zero-sleep to allow underlying connections to close
    # http://aiohttp.readthedocs.io/en/stable/client_advanced.html#graceful-shutdown
    ioloop.run_until_complete(asyncio.sleep(0))
    # ioloop.close()  # don't close the loop, so it's available for re-use 
    # https://stackoverflow.com/questions/45010178/how-to-use-asyncio-event-loop-in-library-function
    return sorted(network_scan.result(), key=lambda x: ipaddress.ip_address(x.hostname))


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
    print('Found {} match{}{}{} on {}'.format(len(result), 'es' if len(result)!=1 else '',
        ' for ' if args.pattern else '', args.pattern, args.network))
    for x in result:
        print(x.hostname)


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
    print(result)
