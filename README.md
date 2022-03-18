# SOA_grpc

Ссылка на DockerHub: https://hub.docker.com/repository/docker/adakimov/grpc

## Тест

Чтобы протестировать приложение :

### Шаг 1

Скачать себе Docker образ серверной части на компьютер.

```
docker push adakimov/grpc:tagname
```

Скачать файл `client.py`.

### Шаг 2

Запускаем сначала server:

```
docker run -it adakimov/sockets
```

Далее заупскаем 4-ёх client-ов из разных консолей:

```
pip3 install pyaudio
pip3 install opencv-python

python client.py 
```

## Интерфейс


### Mute

Чтобы выключить микрофон, нажмите `p`.

### Unmute

Чтобы включить микрофон, нажмите `c`.

### Exit 
Чтобы выйти, нажмите `q`.

### Next Day
Чтобы начать новый день, нажмите `n`.

### Choice person
Чтобы сделать выбор игрока, нажмите кнопку `0-9`, в соотсетсвии с именем игрока.
