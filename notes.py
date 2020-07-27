from datetime import datetime, timedelta
from random import randint
from cloud import CloudRecord
from storage import StorageRecord
from public_ip import PublicIpUsageRecord
from random import choice, choices


class User:
    count = 0

    def __init__(self):
        self.user_id = "user-" + str(User.count)
        self.group_id = "ThisGroup"
        self.global_name = "GLobalNaMe"
        self.site_name = "SiteName"
        self.role = None
        self.cloud_compute_service = None
        self.cloud_type = "OpenNebula??"
        self.vms = []
        User.count += 1

    def generate_vms(self, vm_count):
        for i in range(vm_count):
            cr = CloudRecord()
            cr.set_all({
                "VMUUID": self.user_id + "machine" +  str(len(self.vms) + 1),
                "SiteName": self.site_name,
                "MachineName": "machine" +  str(len(self.vms) + 1),
                "LocalUserId": self.user_id,
                "LocalGroupId": self.group_id,
                "GlobalUserName": self.global_name,
                "CloudComputeService": self.cloud_compute_service,
                "CloudType": self.cloud_type,
                "FQAN": "FQAN",
                "Disk": 0,
                "Memory": 0,
                "PublicIPCount": 0,
                "SuspendDuration": 0,
                "CpuDuration": 0,
                "WallDuration": 0,
                "CpuCount": 0,
                "StorageUsage": 0
                })
            self.vms.append(cr)


def get_storage_json(vm: CloudRecord, time: datetime):
    return {"RecordId": vm.get_field("LocalUserId") + str(time),  # TODO random generate
            "CreateTime": time,
            "StorageSystem": "ss",
            "StorageShare": "50",
            "StorageMedia": "disk",
            "FileCount": "1000",
            "DirectoryPath": None,
            "LocalUser": vm.get_field("LocalUserId"),
            "LocalGroup": vm.get_field("LocalGroupId"),
            "StartTime": time,  # TODO
            "EndTime": time,  # TODO ako tu ma byt start a end
            "ResourceCapacityUsed": vm.get_field("StorageUsage"),
            "LogicalCapacityUsed": vm.get_field("StorageUsage"),
            "ResourceCapacityAllocated": vm.get_field("StorageUsage"),
            "Group": None,  # not sure what
            "Role": None,  # neither here
            "StorageClass": None,
            "UserIdentity": vm.get_field("GlobalUserName")}


def get_ip_json(vm: CloudRecord, time: datetime):
    return {"MeasurementTime": datetime.timestamp(time),
            "SiteName": vm.get_field("SiteName"),
            "CloudComputeService": vm.get_field("CloudComputeService"),
            "CloudType": vm.get_field("CloudType"),
            "LocalUser": vm.get_field("LocalUserId"),
            "LocalGroup": vm.get_field("LocalGroupId"),
            "GlobalUserName": vm.get_field("GlobalUserName"),
            "FQAN": vm.get_field("FQAN"),
            "IPVersion": "dunno", # TODO co s tymto
            "IPCount": vm.get_field("PublicIPCount")
            }


def generate_users(user_count):
    users = []
    for i in range(user_count):
        users.append(User())
    return users


def generate_cron_intervals(cron_interval_count, start_time, end_time = None):
    if end_time is None:
        end_time = datetime.now()
    interval_length = (end_time - start_time) / cron_interval_count
    return [start_time + i*interval_length for i in range(1, cron_interval_count)]


def generate_event_times(event_count, start_time: datetime, end_time: datetime = None):
    if end_time is None:
        end_time = datetime.now()
    interval_length = int((end_time - start_time).total_seconds() / event_count)
    res = [start_time,]
    for i in range(event_count):
        res.append(res[-1] + timedelta(seconds=randint(0.8*interval_length, 1.2*interval_length)))
    return res


def start_machine(vm: CloudRecord, event_time: datetime): #DONE
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    if vm.get_field("Status") == "suspended":
        vm.set_field("SuspendDuration",
                     vm.get_field("SuspendDuration") + (event_time - vm.get_field("SuspendTime")).total_seconds() )
    vm.set_field("Status", "started")
    if vm.get_field("StartTime") is None:
        vm.set_field("StartTime", event_time)
    vm.set_field("CpuChange", event_time)
    print("Machine started at: wall time %s cpu time %s" % (vm.get_field("WallDuration"), vm.get_field("CpuDuration")))


def finish_machine(vm: CloudRecord, event_time: datetime): # DONE
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    if vm.get_field("Status") == "started":
        vm.set_field("WallDuration",
                     vm.get_field("WallDuration") + (event_time - vm.get_field("CpuChange")).total_seconds())
        vm.set_field("CpuDuration",
                     vm.get_field("CpuDuration") +
                     vm.get_field("CpuCount")*(event_time - vm.get_field("CpuChange")).total_seconds())

    if vm.get_field("Status") == "suspended":
        vm.set_field("SuspendDuration",
                     vm.get_field("SuspendDuration") + (event_time - vm.get_field("SuspendTime")).total_seconds())

    vm.set_field("Status", "completed")
    vm.set_field("EndTime", event_time)
    print("Machine finished at: wall time %s cpu time %s" % (vm.get_field("WallDuration"), vm.get_field("CpuDuration")))


def suspend_machine(vm: CloudRecord, event_time: datetime):
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    vm.set_field("Status", "suspended")
    vm.set_field("SuspendTime", event_time)
    if vm.get_field("StartTime") is not None:
        vm.set_field("WallDuration", (event_time - vm.get_field("CpuChange")).total_seconds())
        vm.set_field("CpuDuration", vm.get_field("CpuDuration") + vm.get_field("WallDuration")*vm.get_field("CpuCount"))
    print("Machine suspended, wall time %s cpu time %s" % (vm.get_field("WallDuration"), vm.get_field("CpuDuration")))


def allocate_ip(vm: CloudRecord, event_time: datetime):
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    # version = choice([4,6])
    # if vm.get_field("PublicIpCount") != 0:
    #     last_ip_record = PublicIpUsageRecord.all_records[-1]
    vm.set_field("PublicIPCount", vm.get_field("PublicIPCount") + randint(1,5))


def free_ip(vm: CloudRecord, event_time: datetime):
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    amount = randint(1,5)
    if amount > vm.get_field("PublicIPCount"):
        amount = vm.get_field("PublicIPCount")
    vm.set_field("PublicIPCount", vm.get_field("PublicIPCount") - amount)


def allocate_memory(vm:CloudRecord, event_time : datetime):
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    vm.set_field("Memory", vm.get_field("Memory") + (10^9)*randint(1,16))


def free_memory(vm:CloudRecord, event_time : datetime):
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    amount = (10^9)*randint(1,16)
    if amount > vm.get_field("Memory"):
        amount = vm.get_field("Memory")
    vm.set_field("Memory", vm.get_field("Memory") - amount)


def allocate_storage(vm: CloudRecord, event_time: datetime):
    st = StorageRecord()
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    amount = (10^9)*randint(5,1000)
    vm.set_field("StorageUsage", vm.get_field("StorageUsage") + amount)
    st.set_all(get_storage_json(vm, event_time))


def free_storage(vm: CloudRecord, event_time: datetime):
    st = StorageRecord()
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())

    amount = (10 ^ 9) * randint(5, 1000)
    if amount > vm.get_field("StorageUsage"):
        amount = vm.get_field("StorageUsage")
    vm.set_field("StorageUsage", vm.get_field("StorageUsage") - amount)
    st.set_all(get_storage_json(vm, event_time))


def allocate_cpu(vm: CloudRecord, event_time: datetime):
    amount = randint(1,32)
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    if vm.get_field("Status") == "started":
        print("Time from last change: ", (event_time - vm.get_field("CpuChange")).total_seconds())
        vm.set_field("WallDuration", vm.get_field("WallDuration") + (event_time - vm.get_field("CpuChange")).total_seconds()) #nvm
        vm.set_field("CpuDuration", vm.get_field("CpuDuration")
                     + (event_time - vm.get_field("CpuChange")).total_seconds()*vm.get_field("CpuCount"))
    vm.set_field("CpuChange", event_time)
    vm.set_field("CpuCount", vm.get_field("CpuCount") + amount)

    print("Cpu allocated at " + str(event_time) + " current cpu count: "+ str(vm.get_field("CpuCount")))
    print("wall time %s cpu time %s" % (vm.get_field("WallDuration"), vm.get_field("CpuDuration")))


def free_cpu(vm: CloudRecord, event_time: datetime):
    new_record = CloudRecord()
    new_record.load_from_msg(vm.get_msg())
    amount = randint(1, 32)
    if amount > vm.get_field("CpuCount"):
        amount = vm.get_field("CpuCount")
    print("Time from last change: ", (event_time - vm.get_field("CpuChange")).total_seconds() )
    if vm.get_field("Status") == "started":
        vm.set_field("WallDuration", vm.get_field("WallDuration") + (event_time - vm.get_field("StartTime")).total_seconds())
        vm.set_field("CpuDuration", vm.get_field("CpuDuration")
                     + (event_time - vm.get_field("CpuChange")).total_seconds()*vm.get_field("CpuCount"))
    vm.set_field("CpuChange", event_time)
    vm.set_field("CpuCount", vm.get_field("CpuCount") - amount)

    print("Cpu freed at" + str(event_time) + " current cpu count: "+ str(vm.get_field("CpuCount")))
    print("wall time %s cpu time %s" % (vm.get_field("WallDuration"), vm.get_field("CpuDuration")))


def simulate_life(vm: CloudRecord, events, intervals):
    i, j = 0, 0
    #TODO pridat logy
    for i in range (len(events)):
        memory = vm.get_field("Memory")
        cpu = vm.get_field("CpuCount")
        status = vm.get_field("Status")
        ip = vm.get_field("PublicIPCount")
        storage = vm.get_field("Disk")

        while j < len(intervals) and events[i+1] > intervals[j] > events[i]:
            new_storage_record = StorageRecord()
            new_storage_record.set_all(get_storage_json(vm, intervals[j]))

            new_ip_record = PublicIpUsageRecord()
            new_ip_record.set_all(get_ip_json(vm, intervals[j]))

            cloud_record = CloudRecord()
            cloud_record.load_from_msg(vm.get_msg())

            j += 1

        event = choices([start_machine, finish_machine, suspend_machine, allocate_ip, free_ip, allocate_memory,
                         free_memory, allocate_storage, free_storage, allocate_cpu, free_cpu],
                        k=1,
                        weights=[19, 1, 10, 19, 19, 19, 19, 19, 19,19, 19])[0]

        if memory == 0 and event == free_memory:
            event = allocate_memory
        if cpu == 0 and event == free_cpu:
            event = allocate_cpu
        if storage == 0 and event == free_storage:
            event = allocate_storage
        if ip == 0 and event == free_ip:
            event = allocate_ip

        if status is None and (event == finish_machine or event == suspend_machine):
            event = start_machine

        if status == "suspended" and event == suspend_machine:
            continue
        if status == "started" and event == start_machine:
            continue
        if status == "completed":
            continue

        # print(events[i], event, vm.get_field("VMUUID"))
        event(vm, events[i])


start_time = datetime.now() - timedelta(seconds=1000000)
cron_interval_count = 10
event_count = 20
user_count = 1
cron_intervals = generate_cron_intervals(cron_interval_count, start_time)

users = generate_users(user_count)
for user in users:
    user.generate_vms(randint(2,6))
    for vm in user.vms:
        events = generate_event_times(event_count, start_time)
        simulate_life(vm, events, cron_intervals)
        print("DEATH")

# for r in StorageRecord.all_records:
#     print(r.get_ur())
