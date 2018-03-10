""" Demo file of use """
import httpscan

NETWORK = '192.168.0.0/24'

result = httpscan.survey(network=NETWORK, 
    pattern='(P|p)hilips',
    path='description.xml',
    log=False)

result.sort()
print(result)
