Src https://github.com/gogs/gogs
Docker usage doc https://github.com/gogs/gogs/tree/main/docker

# folder struct 
'''
/data
|-- git
|   |-- gogs-repositories
|-- ssh
|   |-- # ssh public/private keys for Gogs
|-- gogs
    |-- conf
    |-- data
    |-- log

'''

# networking
 * SSH Port: Use the exposed port from Docker container. For example, your SSH server listens on 22 inside Docker, but you expose it by 10022:22, then use 10022 for this value. Builtin SSH server is not recommended inside Docker Container
 * HTTP Port: Use port you want Gogs to listen on inside Docker container. For example, your Gogs listens on 3000 inside Docker, and you expose it by 10880:3000, but you still use 3000 for this value.
 * Application URL: Use combination of Domain and exposed HTTP Port values (e.g. http://192.168.99.100:10880/).

 # usage
 * run.sh - run container in interactive mode
 * up.sh - run and detach