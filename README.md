# Ray Open Ports Checker

This repo contains a utility the Ray project is releasing to help Ray users
validate that their clusters are not incorrectly configured in a way that might
allow untrusted clients to run arbitrary code on their clusters.

## What does this do?

It runs a set of Ray tasks across the cluster to collect the list of ports Ray
is currently using. Each node then sends its local set of active ports to a
service operated by the Ray team running on the public internet which then
attempts to connect back and validate if they're accessible. If any are found to
be accessible, the script will report the details.

## Known limitations

- [ ] This tool depends on symmetric inbound and outbound network
      configurations. If you are using custom firewall rules or NAT rules that
      modify that, including by redirecting ports, routing connections across
      different IP addresses, use of this tool may result in false negatives.
- [ ] Clusters running on kubernetes (via KubeRay) or other container based
      deployment mechanisms may result in false-negatives. This is because the
      port that Ray believes it is running on may not correctly reflect the port
      on the underlying host, or the network topology around the host.

## Example Output

### No open ports detected

```
Cluster has 26 node(s). Scheduling tasks on each to check for exposed ports
[🟢] No open ports detected checked_ports=[6822, 6823, 8076, 8085, 8912, 10002, 44973] node='defb6868434e23ba21c3f9fc84ec523f1378b11e5d289547234edb07'
[...]
[🟢] No open ports detected checked_ports=[6822, 6823, 8076, 8085, 8912, 10002, 10003, 10004, 10005, 60094] node='d368a5fdbe8147bdefafbf9eb4358eae796c168f24f1b297e13a0af6'
Check complete, results:
[🟢] No open ports detected from any Ray nodes
```

### Open ports detected

```
Cluster has 26 node(s). Scheduling tasks on each to check for exposed ports
[🟢] No open ports detected checked_ports=[6822, 6823, 8076, 8085, 8912, 10002, 44973] node='defb6868434e23ba21c3f9fc84ec523f1378b11e5d289547234edb07'
[...]
[🛑] open ports detected open_ports=[8265] node='53fca104c1bb17cd3e996b01e0900aa2a24c2f473d845f56eb3f7aa2'
[...]
[🟢] No open ports detected checked_ports=[6822, 6823, 8076, 8085, 8912, 10002, 10003, 10004, 10005, 60094] node='d368a5fdbe8147bdefafbf9eb4358eae796c168f24f1b297e13a0af6'
Check complete, results:
[🛑] An server on the internet was able to open a connection to one of this Ray
cluster's public IP on one of Ray's internal ports. If this is not a false
positive, this is an extremely unsafe configuration for Ray to be running in.
Ray is not meant to be exposed to untrusted clients and will allow them to run
arbitrary code on your machine.

You should take immediate action to validate this result and if confirmed shut
down your Ray cluster immediately and take appropriate action to remediate its
exposure. Anything either running on this Ray cluster or that this cluster has
had access to could be at risk.

For guidance on how to operate Ray safely, please review [Ray's security
documentation](https://docs.ray.io/en/master/ray-security/index.html).
```

## Instructions

The checker script
([checker.py](https://github.com/ray-project/ray-open-ports-checker/blob/main/checker.py))
can be found in the root of this repo. It is meant to be easy to deploy by being
a single file python script with zero dependencies beyond Ray itself.

### Deployment ideas:

- Copy to your head node, and run it
- Use the Ray Job Submission APIs
- Use Ray Client

## Q&A:

- Why can't this run purely offline? / Why do you need to talk back to an
  external server?

  - Local network configurations can be misleading Software binding to 0.0.0.0
    does not mean it is accessible to the internet is the vast majority of
    deployment scenarios.
  - By performing an end to end check against a server on the internet it
    reduces the likelihood of false positives.
  - Also: If you don't want to use the Ray Teams' hosted server, you can host
    your own. The full source code is in the `server` folder.

- What are my other options?
  - This script is automating the process of identifying all the nodes in your
    Ray cluster and asking a server on the internet if there are any tcp ports
    accessible to it. You can perform a similar check using any of the publicly
    available port scanning tools.
  - Please feel free to examine how this works and adapt it to your needs, it
    should work out of the box, but please feel free to customize to your needs.

## Privacy

Please note that if you utilize Anyscale’s hosted server: we may collect
information in accordance with our [privacy
policy](http://anyscale.com/privacy-policy) sent to the server (e.g., IP
address, open ports) to help improve Ray and determine the extent to which these
misconfigurations continue to be an issue.
