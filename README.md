# Embedded Cluster test app

## Redis backup and restore test

`alpine-redis` runs Redis with a 128 MiB PVC mounted at `/data`. It saves
RDB snapshots periodically and loads `/data/dump.rdb` on startup. Velero pod
annotations run a synchronous `SAVE` before backing up the volume and fail
the backup if Redis does not return `OK`.

Redis opts into Velero filesystem backups with the `backup-volumes` annotation.
On EC v2, use KOTS snapshots through the Admin Console; the app's Velero chart
is excluded when `KotsVersion` is nonempty. On EC v3 without KOTS, the app
includes its own Velero chart. Redis's pod annotations work with either path
and do not depend on the EC v3 vendor backup hooks.

Using your app namespace, write a marker before taking a backup:

```sh
kubectl -n <app-namespace> exec deployment/alpine-redis -- redis-cli SET restore-test before-backup
```

Take a snapshot through the Admin Console on EC v2 (or a backup through
Embedded Cluster on EC v3) and wait for it to complete. Change the
marker afterward so you can distinguish restored data from the live database:

```sh
kubectl -n <app-namespace> exec deployment/alpine-redis -- redis-cli SET restore-test after-backup
kubectl -n <app-namespace> exec deployment/alpine-redis -- redis-cli SAVE
```

Restore the backup into a clean recovery environment with no existing Redis PVC.
Once `alpine-redis` is ready, read the marker:

```sh
kubectl -n <app-namespace> exec deployment/alpine-redis -- redis-cli GET restore-test
```

The expected result is `before-backup`. Restarting a pod with its existing PVC
does not test recovery from backup.
