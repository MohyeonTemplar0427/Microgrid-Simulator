# Oracle Always Free website pilot

Status: **private VM preparation in progress**. The Oracle VM, owner-controlled
domain, DNS record, and Auth0 tenant/application exist. Python dependencies and
Caddy are installed on the VM; the Auth0 client secret is stored only in its
private API settings file. No application source or public website has been
deployed, and the API, worker, and Caddy services remain stopped. The pilot uses
the reviewed deployment package in
[Web_Deployment_Package.md](Web_Deployment_Package.md). Keep Web UI v1.0.2 and
the engine snapshot tied to the reviewed release; do not deploy an uncommitted
working tree.

## Chosen pilot stack

- One Oracle Cloud Infrastructure (OCI) **Always Free** Ampere A1 Ubuntu VM,
  within **2 OCPUs and 12 GB RAM** total. Oracle currently includes **200 GB of
  block storage including the boot volume**. Choose an Always Free-eligible
  shape and image, and confirm the console's projected cost is zero before
  creating anything. Free capacity can be unavailable and idle free VMs can be
  reclaimed. Do not substitute a paid shape or upgrade the account silently.
- A domain registered and controlled by the site owner. Use a subdomain such
  as `sim.YOUR_DOMAIN` for the pilot. Domain registration and renewal may cost
  money even when the VM and Auth0 plans are free.
- Auth0 Free for OpenID Connect sign-in, using a **Regular Web Application**
  with a confidential client. Start with only invited testers and guest studies
  disabled. The application keeps its own private server-side sessions.
- Caddy for HTTPS; Waitress and the study worker stay on the VM. Only ports
  80/443 are public. The study database and files stay private on persistent
  storage.

This is a pilot target, not a capacity promise. A local, wheel-only pip
resolution for the exact `requirements.txt` completed for CPython 3.13 Linux
Arm64 using compatible `manylinux_2_28_aarch64` and
`manylinux2014_aarch64` tags on 2026-09-27. It does not test imports,
OpenDSS, optimizer behavior, runtime, or disk use on an OCI VM. Run those
checks before permitting real users.

## What you set up in your own accounts

1. **Register a domain.** Use any domain registrar you trust. Keep access to
   its DNS settings, enable account MFA, and note its renewal date. Decide the
   exact pilot hostname, for example `sim.YOUR_DOMAIN`. Do not send the domain
   registrar password or Auth0 client secret through chat.
2. **Create an OCI Free Tier account.** Oracle usually requires phone and card
   verification, but says the card is not charged unless you upgrade. Choose
   the home region carefully: Always Free compute must run there. Create one
   Ubuntu Arm A1 VM with an SSH key, a public IPv4 address, and no more than
   the free CPU, RAM, and storage allocation. OCI may report no available A1
   capacity; if so, try another availability domain in that home region or
   wait. Avoid the 1 GB AMD micro VM for this numerical workload.
3. **Set OCI network rules.** Allow inbound TCP 80 and 443 to the VM. Limit
   inbound SSH port 22 to your own IP if possible. Do not open port 8765 or
   the database. Configure the Ubuntu host firewall consistently with the OCI
   network security rules. Record the VM's public IPv4 address.
4. **Point your domain to the VM.** In your registrar's DNS page, add an `A`
   record for host `sim` whose value is the VM's public IPv4 address. If you
   choose the root domain, use the registrar's root/`@` host instead. Do not
   leave an unrelated `AAAA` record for this hostname unless IPv6 is also
   configured on the VM. An ephemeral OCI public IP stays with a stopped VM,
   but can change if that VM is terminated and recreated; update the DNS
   record then. From your computer, verify `dig +short sim.YOUR_DOMAIN A`
   returns the VM's IPv4 address before trying HTTPS.
5. **Create an Auth0 Free tenant and Regular Web Application.** Select
   Authorization Code, PKCE S256, RS256 ID tokens, and Client Secret Basic
   authentication. Set its allowed callback URL to exactly
   `https://sim.YOUR_DOMAIN/auth/callback`. Enable only the sign-in connection
   intended for this pilot; disable public sign-ups on that connection if
   access is by invitation. Keep its Client ID and Client Secret private.
   Auth0's tenant issuer is generally shaped like
   `https://YOUR_TENANT.REGION.auth0.com/`; copy the exact issuer value from
   Auth0 discovery rather than guessing it.

The DNS name can be chosen before the VM, but the `A` record needs the VM's
public IP. The Auth0 callback needs the final HTTPS hostname. A later domain
change also requires changing both hosted environment values and the allowed
Auth0 callback, then restarting the API and Caddy.

## Values to connect on the VM

Populate `/etc/microgrid/api.env` privately from
`deploy/systemd/api.env.example` and `/etc/microgrid/caddy.env` from its
example. The corresponding values must be identical:

```text
MICROGRID_PUBLIC_ORIGIN=https://sim.YOUR_DOMAIN
MICROGRID_SITE_ADDRESS=https://sim.YOUR_DOMAIN
MICROGRID_OIDC_REDIRECT_URI=https://sim.YOUR_DOMAIN/auth/callback
MICROGRID_OIDC_ISSUER=https://YOUR_TENANT.REGION.auth0.com/
```

`MICROGRID_SITE_ADDRESS` goes only in `caddy.env`; the others go in
`api.env`. The Auth0 Client ID and Client Secret also go only in `api.env`.
The worker must never receive the OIDC secret. Never commit these files or
paste their contents into an issue or chat. Keep `--allow-guests` off for the
pilot. Follow the host preparation, backup, service installation, and test
sequence in [Web_Deployment_Package.md](Web_Deployment_Package.md).

The Caddy certificate can be issued only after DNS points to the VM and ports
80/443 reach Caddy. The current app's logout revokes its own session; it does
not end the separate Auth0 single sign-on session. Test this behavior with
pilot users, especially on shared computers, before broad access.

## Pilot acceptance before inviting users

- Confirm Python 3.13 and **all pinned dependencies** install on the actual
  Arm VM. Run `tools.prepare_web_release` and a representative end-to-end
  simulation, including OpenDSS and result download.
- Check a real HTTPS certificate, exact Auth0 callback, two-account study
  isolation, API loopback binding, and that no secret appears in logs.
- Measure peak RAM, CPU, runtime, and actual live and seven-day backup disk
  use. Reduce the example storage and study quotas to fit the free volume;
  the defaults are not a capacity assessment for this VM.
- Test backup, restore to a separate directory, and seven-day pruning.
  Backups kept only on the same VM do **not** survive loss of the VM or disk;
  arrange separately protected backups before relying on the service.
- Keep registration closed and the invitation list small until these checks
  pass. OCI's free-capacity and idle-reclamation rules make this a trial host
  rather than an availability guarantee.

## Sources checked 2026-09-27

- [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
  and [Oracle Free Tier signup](https://docs.oracle.com/en/learn/cloud_free_tier/).
- [Oracle public IP behavior](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm)
  and [security rules](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securityrules.htm).
- [Caddy automatic HTTPS requirements](https://caddyserver.com/docs/automatic-https).
- [Auth0 Free plan](https://auth0.com/pricing),
  [Regular Web Applications](https://auth0.com/docs/get-started/auth0-overview/create-applications/regular-web-apps),
  and [confidential client methods](https://auth0.com/docs/get-started/applications/confidential-and-public-applications).
