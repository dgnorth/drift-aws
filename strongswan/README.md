# strongSwan VPN Setup for Drift VPC's.
[strongSwan](http://www.strongswan.org/) is an OpenSource IPSec-based VPN solution. It runs on pretty much anything.

### StrongSwan Installation for OS X:
Use [Homebrew](http://brew.sh/) to install StrongSwan:
`brew install strongswan`

### Configuring StrongSwan for VPC's:
*Note that almost all of these actions require root access.*

Generate a PSK, like this: `openssl rand -hex 20`



* Copy *ipsec.conf* and *ipsec.secrets* to your `/usr/local/etc` folder using the *sync-ipsec-to-local-osx* shell script.
* Run `ipsec restart`

### Connecting to a VPN:
Connect to a VPN using `ipsec up` command, i.e.: `ipsec up deveast`

To see which connections are available, run `list-available-connections`

### Testing connection:
Run `ipsec status` to see which connections are active.

If you have a successfull connection, you should be able to ping any EC2 instance on the VPC, and you should be able to ping your computer from any EC2 instance from within the VPC.

If something is not working, try shut down the connection and invoke it again, i.e.:

```
ipsec down mytiername
ipsec up mytiername
```
