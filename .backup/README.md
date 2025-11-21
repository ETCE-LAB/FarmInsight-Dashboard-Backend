
This README explains how to load the backup into the (InfluxDB) docker container.

To get the backup data go to https://github.com/ETCE-LAB/FarmInsight-Dashboard-Backend/tree/backup and download the two .tar files.
```
backup.tar
backup_engine_data.tar
```

To circumvent Githubs 100MB file size limit and avoid having to install git lfs into the repo the backup.tar were into 2 files so you need to manually copy the files from backup_engine_data.tar into the backup.tar\var\engine\data.

On Windows:
You now need to copy the backup.tar file into the WSL file space, else the mounting into the docker won't work 
(Mac/Linux can skip this step).

Open WSL and inside the shell copy it by using cp like so (if you have the backup.tar in the downloads folder on the C drive):
```
cp /mnt/c/Uers/<windows.username>/Downloads/backup.tar
```

Now you should have the complete backup.tar in the current shell working directory from there you can use this command to copy the contents into the volume of an existing Influx container as created by the compose.yaml.
```
docker run --rm --volumes-from farminsight-dashboard-backend-influxdb-1 -v $(pwd):/backup influxdb:latest bash -c "cd var/lib/influxdb2 && tar xvf /backup/backup.tar --strip 1"
```

If the docker container run successfully, you are all done!

<br>
<br>

To explain the configurable parts of the command to help debugging (hopefully not needed):

farminsight-dashboard-backend-influxdb-1 is the name of the container you want to dump the backup into that's the default name from using the compose.yaml on my system, this could be different if you want to move it into a differently named influx container.
```
-v $(pwd):/backup  mounts the current directory [$(pwd)] into the container as /backup
```
influxdb:latest is the image we use for the influx container

```
bash -c "cd var/lib/influxdb2 && tar xvf /backup/backup.tar --strip 1" 
```
runs the command in the quotation marks inside the container, in this case it makes var/lib/influxdb2 the working directory, and unzips the backup.tar into there.