This scripts exports zones from a powerdns.net hosting into bind style zonefiles

setup:


    mkdir /var/mydnszones
    powerdnsnet-to-zonefiles.py <your-api-key> /var/mydnszones # <- run this as a cronjob 



to serve the zones from a powerdns authoritative server, add this to your pdns.conf:

    launch=bind
    bind-config=/var/mydnszones/named.conf
    bind-check-interval=300
    


