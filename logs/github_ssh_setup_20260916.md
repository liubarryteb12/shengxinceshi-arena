# GitHub SSH setup

- Remote: `git@github.com:liubarryteb12/shengxinceshi-arena.git`
- Key type: ED25519
- Fingerprint: `SHA256:d61Gdml0PP0rJdoKhS/HKc2CdrhLPgRkfpTSoTh/j3k`
- Public key to add to the `liubarryteb12` GitHub account:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP6U8wbjpaGzyhAGw4a+JHyjZOTIqFTAq4NX96BbWtl7 shengxinceshi-arena-agent@arena.ai
```

The private key remains outside the repository at `/home/user/.ssh/id_ed25519` and is not written to version control.

After the public key is added under GitHub Settings → SSH and GPG keys, the next push can use the SSH remote. No GitHub password or personal access token needs to be placed in the repository.
