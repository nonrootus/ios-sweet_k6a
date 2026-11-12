# ios-sweet_k6a

**iOS 16 на Redmi Note 12 Pro 4G (`sweet_k6a`, Snapdragon 732G / SM7150, Adreno 618).**

> **English summary.** A port of Apple's open-source XNU kernel (xnu-8796, iOS 16 generation) to the
> Redmi Note 12 Pro 4G, running the unmodified iOS 16.7.16 (20H392) userland of the iPhone X. The UI
> is drawn by the phone's Adreno 618 GPU through Mesa freedreno behind CoreAnimation's OpenGL ES
> renderer, with our own kernel GPU driver. All eight CPU cores run, there is a rootful jailbreak
> (Procursus, Sileo, ElleKit tweaks, OpenSSH) and internet over the USB cable (RNDIS). Wi-Fi, sound,
> camera, cellular, brightness and the flashlight do not work. Experimental, not a daily-driver OS.
> Based on [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) (Redmi Note 10 Pro).

> Экспериментальный порт, не телефон на каждый день. iOS ставится в раздел `userdata`, **данные
> Android стираются**. Ядро грузится временно через `fastboot boot`: загрузчик, recovery, модем,
> persist и разделы загрузки не прошиваются. Прошивка iOS (IPSW) и файлы Apple в репозитории не
> лежат, их каждый берёт сам.

## Что это

- Ядро — открытый XNU от Apple (xnu-8796.141.3) с нашими патчами (`xnu/patches/`, сейчас до 0225),
  собирается в GitHub Actions (`.github/workflows/xnu.yml`, macOS-раннер, darwin-xnu-build).
- Поверх него работает **настоящий userland iPhone X**: iOS 16.7.16 (20H392), launchd, системные
  демоны, backboardd, SpringBoard, штатные приложения.
- Загрузка: стоковый загрузчик Xiaomi → `fastboot boot` нашего образа (shim + XNU + device tree) →
  XNU. Корень iOS — HFS+ в `userdata`.
- Телефон представляется iOS как iPhone X (`iPhone10,3`), экран как панель 1125×2436.

Проект продолжает [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) (тот же порт для
Redmi Note 10 Pro, `sweet`). Всё, что касается `sweet_k6a` и GPU, сделано здесь. Прежний README
апстрима лежит в [`docs/UPSTREAM-README.md`](docs/UPSTREAM-README.md).

## Что работает

| Что | Состояние |
| --- | --- |
| Загрузка | `fastboot boot` временного образа; iOS доходит до рабочего стола |
| Процессор | Все 8 ядер (6× Cortex-A55 + 2× Cortex-A76), свой регулятор частоты: A55 до 1804 МГц, A76 до 2304 МГц |
| GPU | **Adreno 618 рисует весь интерфейс.** Свой драйвер в ядре (GMU, HFI, SMMU, кольцо команд CP), Mesa freedreno (OSMesa) за OpenGL ES-рендером CoreAnimation |
| Плавность | Асинхронная отправка работы на GPU с fence (0215): медиана кадра 4–8 мс, тяжёлые анимации 14–16 мс. Поток рендера на быстрых A76 (0203, 0217). Нулевое копирование IOSurface (0206–0208), BGRA-поверхности через sRGB-дерево устройства |
| Интерфейс | Экран блокировки, рабочий стол, пункт управления, центр уведомлений, Настройки, штатные приложения |
| Тач и кнопки | Тачскрин, питание, громкость (из апстрима) |
| Джейлбрейк | Rootful: бутстрап Procursus (от palera1n), Sileo, NewTerm, OpenSSH, твики через ElleKit (`DYLD_INSERT_LIBRARIES` разрешён политикой AMFI в ядре, 0213). apt работает (заглушка `libkrw0-plugin`) |
| USB | Консоль ядра (ACM) и сеть RNDIS одновременно (`sweetusb=4`, 0211, 0216–0219). Windows видит телефон как сетевой адаптер без драйверов |
| Интернет | По кабелю: общий доступ Windows (ICS) → телефон 192.168.137.2. Safari, Sileo, SSH (`root@192.168.137.2`) |
| Приложения | Расшифрованные .ipa ставятся в `/Applications` по SSH + `uicache` и запускаются |

## Что не работает

- **Wi-Fi, Bluetooth, сотовая связь, звук, камера, фонарик, вибро** — нет драйверов. Для Wi-Fi есть
  готовая схема у порта K20 Pro (WCN3990 через ICNSS + модем + ath10k), у нас то же железо, но перенос
  не делался.
- **Яркость.** Попытка (0220: команда DCS 0x51 по DSI + `AppleARMBacklight`) сломала картинку и
  уронила телефон, патч убран. Разбор — в `NOTES.md`.
- **Metal** — нет. Большинство современных игр (Unity, Unreal) рисуют через Metal и не запустятся;
  у игр на OpenGL ES шанс есть.
- **USB-сеть нестабильна.** Через несколько минут работы (быстрее под нагрузкой и если общий доступ
  в Windows включён ещё до загрузки телефона) Windows теряет ответ по управляющему каналу RNDIS,
  сбрасывает каналы, и связь пропадает до переподключения кабеля. Патчи 0222–0225 эту причину не
  нашли (они безвредны и оставлены). Большие файлы удобнее копировать кусками
  (`tools/local-pipeline/helpers/copy-in-pieces.ps1`).
- **Простой процессора (WFI) выключен** (`wfi=0`), поэтому телефон греется даже без дела. Путь с
  включённым простоем (0209, 0210, 0212, 0214) написан, но до конца не проверен: 0212 давал чёрный
  экран, 0214 должен это исправлять.
- **Джейлбрейки для настоящих айфонов** (Dopamine, Serotonin) не работают: они взламывают ядро Apple,
  а здесь своё. Dopamine падает (нет arm64e-библиотеки), Serotonin роняет ядро в панику.
- Иногда iOS сама перезапускается (яблоко без перезагрузки ядра): системный сторож находит зависший
  процесс.
- Безопасность Apple в основном выключена: AMFI, песочница и т.п. Не храните на нём ничего важного.

## Как устроен репозиторий

| Путь | Что там |
| --- | --- |
| `xnu/patches/` | Патчи к XNU по порядку (0001–0225). Каждый с описанием в начале; генераторы последних — в `tools/local-pipeline/patch-generators/` |
| `xnu/gpu/`, `xnu/cpufreq/` | Исходники драйвера GPU и регулятора частоты (зеркала файлов, которые вносят патчи) |
| `shim/` | Загрузочный shim: стартует на ядре, которое отдаёт загрузчик, будит нужные ядра и передаёт управление XNU |
| `tools/` | Сборка ядра и образов, генерация дерева устройства (`mkadt.py`), сборка корня iOS (`mkiosroot.sh`), рендера (`build-sweet-renderer.sh`), разбор логов |
| `userland/gpu/` | Патчи к EAGL/Mesa и наши библиотеки для рендера CoreAnimation на GPU |
| `userland/jb/` | `sweetnet`: публикует USB-сеть (`ue0`) в configd, чтобы приложения видели интернет |
| `tools/local-pipeline/` | Скрипты, которыми собирались образы, корень с джейлом и ставились приложения (как есть, с путями `D:\ios-sweet\...`; см. README там) |
| `NOTES.md` | Полный рабочий журнал: каждая сборка, загрузка, замеры и ошибки |
| `docs/` | Документы по GPU, выводу на экран, тестам в QEMU |

## Сборка (кратко)

1. **Ядро:** GitHub Actions `xnu` (workflow_dispatch) — накладывает `xnu/patches/` на xnu-8796.141.3
   и собирает `kernel.development.sweet`; отдельная задача собирает рендер (Mesa + EAGL).
2. **Корень iOS:** IPSW iPhone X 20H392 (берёте сами) → `tools/mkiosroot.sh` → образ HFS+ для
   `userdata`. Джейл-корень поверх него — `tools/local-pipeline/jb/mk-jb-root.sh`.
3. **Загрузочный образ:** shim + ядро + дерево устройства + рамдиск рендера
   (`tools/local-pipeline/`), затем `fastboot boot`.
4. **Интернет:** образ с `sweetusb=4`, в Windows — общий доступ к интернету на адаптер «Remote NDIS».

Подробности, номера сборок и все грабли — в `NOTES.md`.

## Благодарности и лицензии

- [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) и его авторы (dipa-studio,
  damjankakak3, legendxdevil и другие) — основа порта. Лицензия MIT (`LICENSE`).
- Apple — XNU (APSL 2.0). Патчи к XNU — производные XNU и подчиняются APSL 2.0.
- [Mesa](https://mesa3d.org/) / freedreno (MIT).
- [MakrSas/ios-topaz](https://github.com/MakrSas/ios-topaz) — EAGL-рендер для CoreAnimation; его
  `eagl.c` скачивается при сборке рендера, в репозиторий не входит.
- HackiOS (oosexgang, APSL 2.0 / MIT) и
  [HeliumStudio-Dev/hackios-xnu-kernel](https://github.com/HeliumStudio-Dev/hackios-xnu-kernel)
  (порт на K20 Pro) — справочник по железу Qualcomm.
- [syncmodz/ios-s9](https://github.com/syncmodz/ios-s9) (MIT) — способ сборки джейл-корня и `s9net`,
  из которого сделан `sweetnet`.
- palera1n / Procursus, Sileo, ElleKit, blacktop/darwin-xnu-build.

iOS, IPSW, товарные знаки Apple и прошивки телефона в репозиторий не входят.
