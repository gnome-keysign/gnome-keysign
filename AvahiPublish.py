import dbus
import gobject
import avahi
from dbus.mainloop.glib import DBusGMainLoop

serviceName = "Demo Service"
serviceType = "_demo._tcp" # See http://www.dns-sd.org/ServiceTypes.html
servicePort = 1234
serviceTXT = "somethingcrazy" #TXT record for the service

domain = "" # Domain to publish on, default to .local
host = "" # Host to publish records for, default to localhost

group = None #our entry group
rename_count = 12 # Counter so we only rename after collisions a sensible number of times

def add_service():
    global group, serviceName, serviceType, servicePort, serviceTXT, domain, host
    if group is None:
        group = dbus.Interface(
                bus.get_object( avahi.DBUS_NAME, server.EntryGroupNew()),
                avahi.DBUS_INTERFACE_ENTRY_GROUP)
        group.connect_to_signal('StateChanged', entry_group_state_changed)

    print "Adding service '%s' of type '%s' ..." % (serviceName, serviceType)

    group.AddService(
            avahi.IF_UNSPEC,    #interface
            avahi.PROTO_UNSPEC, #protocol
            dbus.UInt32(0),                  #flags
            serviceName, serviceType,
            domain, host,
            dbus.UInt16(servicePort),
            avahi.string_array_to_txt_array(serviceTXT))
    group.Commit()

def remove_service():
    global group

    if not group is None:
        group.Reset()

def server_state_changed(state):
    if state == avahi.SERVER_COLLISION:
        print "WARNING: Server name collision"
        remove_service()
    elif state == avahi.SERVER_RUNNING:
        add_service()

def entry_group_state_changed(state, error):
    global serviceName, server, rename_count

    print "state change: %i" % state

    if state == avahi.ENTRY_GROUP_ESTABLISHED:
        print "Service established."
    elif state == avahi.ENTRY_GROUP_COLLISION:

        rename_count = rename_count - 1
        if rename_count > 0:
            name = server.GetAlternativeServiceName(name)
            print "WARNING: Service name collision, changing name to '%s' ..." % name
            remove_service()
            add_service()

        else:
            print "ERROR: No suitable service name found after %i retries, exiting." % n_rename
            main_loop.quit()
    elif state == avahi.ENTRY_GROUP_FAILURE:
        print "Error in group state changed", error
        main_loop.quit()
        return




if __name__ == '__main__':
    DBusGMainLoop( set_as_default=True )

    main_loop = gobject.MainLoop()
    bus = dbus.SystemBus()

    server = dbus.Interface(
            bus.get_object( avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER ),
            avahi.DBUS_INTERFACE_SERVER )

    server.connect_to_signal( "StateChanged", server_state_changed )
    server_state_changed( server.GetState() )


    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass

    if not group is None:
        group.Free()