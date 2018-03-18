""" Demo file of use """
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
