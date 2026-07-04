# YADRO GPU Lab

## Лабораторный стенд на базе серверов YADRO VEGMAN S320

### Серверы

| Параметр | 40.51 ✅ | 40.50 ❌ |
|---|---|---|
| **Модель** | YADRO VEGMAN S320 | YADRO VEGMAN S320 |
| **CPU** | 2× Xeon Gold 6258R, 56 ядер / 112 потоков | 2× Xeon Gold 6258R |
| **RAM** | 754 GB DDR4 (12×64 GB Samsung) | 768 GB DDR4 |
| **GPU** | 2× NVIDIA RTX 6000/8000 (TU102GL) | 2× NVIDIA RTX 6000/8000 |
| **OS** | Astra Linux 1.8 | Не загружается |
| **IP** | 10.129.13.78 (VLAN 308) | — |
| **Бут-диск** | Intel 480 GB SSD (Marvell RAID1) | Intel 480 GB SSD (RAID потерян) |
| **Данные** | 1.7T + 8× 3.5T SAS SSD | 12× SAS SSD (не настроены) |

### Схема подключения

```dot
digraph YADRO_Lab {
    // Подробная схема в network-topology.dot
}
```

![Сетевая топология](network-topology.svg)

### Как мы к этому пришли

1. **Подключение к BMC** через VPS2 (SSH-туннели 9443/9444)
2. **Попытка установки RED OS 8.0.2** — баг в Anaconda (`reinitialize_locale`)
3. **Попытка установки Ubuntu** на 40.51 через Virtual Media ISO
4. **Проблемы с сетью** — тестовая зона VLAN 308 без интернета
5. **Сканирование сети 10.129.13.0/24** — обнаружено 50 хостов с SSH
6. **Идентификация серверов** по MAC-адресам через ARP с bootsman-dlp (.56)
7. **40.51** — загружен, настроен VLAN 308, SSH root/root
8. **40.50** — проблема с Marvell RAID, диски не видны в BIOS (батарейка CMOS, время 2001 год)

### Доступ

- **BMC 40.50**: https://localhost:9443 (через SSH-туннель skhome01→VPS2)
- **BMC 40.51**: https://localhost:9444 (через SSH-туннель skhome01→VPS2)
- **40.51 SSH**: root/root@10.129.13.78 (через .21 → тестовая зона)
- **.21 (Astra)**: RDP localhost:3389, svlkravchuk/!QAZxsw2123
