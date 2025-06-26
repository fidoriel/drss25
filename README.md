# drss25

Install yaramo: `uv sync`
Install sumo: `uv pip install "eclipse-sumo==1.21.0"`
Use sumo gui `sumo-gui`

Command to run sumo with config file:
```
sumo-gui --remote-port 9090 --configuration-file sumo-config/weiche.scenario.sumocfg
```

notes to reproduce working setup
```
 sudo ip addr add 172.20.5.121 dev enp2s0f0

 sudo ip route add default via 172.20.5.121

 sudo docker compose up -d ntp

 sudo docker compose up -d interlocking_bridge

 python3 pylynx-point-webserver.py 

 curl 127.0.0.1:5000/turn_right

 python gen_weiche_mit_fahrstraße.py

 sumo-gui --remote-port 9090 --configuration-file sumo-config/weiche.scenario.sumocfg
 ```