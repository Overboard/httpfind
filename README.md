# **httpfind**

[![The MIT License](https://img.shields.io/badge/license-MIT-orange.svg?style=flat-square)](http://opensource.org/licenses/MIT)

> Search network for HTTP servers using a regular expression filter.

Use *httpfind* to obtain the IP addresses of specified devices on a network.
HTTP requests for a user specified page are sent in parallel.  Responses are
compared against a user specified regular expression pattern.  Qualified results
are returned as a list.  The module is readily imported for use in other projects,
and it also includes a convenient command line interface.

## Installation

```shell
pip install httpfind
```

## Examples

Basic import example

```python
import httpfind

result = httpfind.survey(
    network='192.168.0.0/24',
    pattern='(A|a)ccess (P|p)oint',
    path='login.php',
    log=False)

# Results printed as full URLs
print(result)
# Results printed as IP addresses
print([x.hostname for x in result])
```

Yields

```shell
['http://192.168.0.190/login.php', 'http://192.168.0.191/login.php', 'http://192.168.0.192/login.php']
['192.168.0.190', '192.168.0.191', '192.168.0.192']
```

Command line example

```shell
$> httpfind -h
usage: httpfind [-h] [-p PATH] [-f PATTERN] [-l] network

Search 'network' for hosts with a response to 'path' that matches 'filter'

positional arguments:
  network               IP address with optional mask, e.g. 192.168.0.0/24

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  URL path at host, e.g. index.html
  -f PATTERN, --filter PATTERN
                        Regular expression pattern for filter
  -l, --log             Enable logging

$> httpfind 192.168.0.0/24 -f "Access Point" -p login.php
Scanning, please wait ...
Found 3 matches for Access Point on 192.168.0.0/24
192.168.0.190
192.168.0.191
192.168.0.192
```

## Parameters

`def survey(network=None, path='', pattern='', log=False):`

* `network` - IP address and subnet mask compatible with
[ipaddress library](https://docs.python.org/3/library/ipaddress.html#ipaddress.ip_network)
* `path` - Path portion of a URL as defined by
[url(un)split](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlsplit)
* `pattern` - A regular expression pattern compatible with
[re.compile](https://docs.python.org/3/library/re.html#re.compile)
* `log` -  boolean to control logging level

Consequently, the network can be defined in either subnet mask (x.x.x.x/255.255.255.0)
or CIDR notation (x.x.x.x/24).  Presently, *httpfind* only scans networks of upto 256
addresses as shown in most of the examples.  Of course, a single IP address may be
specified either by x.x.x.x or x.x.x.x/32.

There are numerous resources for regular expressions, such as the
[introduction](https://docs.python.org/3/howto/regex.html) provided by the Python
Software Foundation.  For the simple cases, using the default or '' will match any
pages while a word such as 'Access' will match if it's found in the returned HTML
provided it's the same case.

## Performance

As *discoverhue* utilizes the excellent [aiohttp](http://aiohttp.readthedocs.io/en/stable/)
package, requests are sent simultaneously rather than iteratively.  More accurately,
the requests are sent randomly over a 2.5s interval so as to not spike traffic.
The timeout is set for 5.0s, so typical execution time is about 8.0s.

## Contributions

Welcome at <https://github.com/Overboard/httpfind>

## Status

Released.
