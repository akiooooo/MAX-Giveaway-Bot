# Подготовленные улучшения

Ветка [prepared-improvements](https://github.com/akiooooo/MAX-Giveaway-Bot/tree/prepared-improvements) содержит 100 реальных коммитов, подготовленных заранее. Большинство изменений расширяет регрессионные тесты; отдельные шаги исправляют обнаруженные дефекты. Это не 100 новых возможностей приложения.

Каждый шаг добавляет самостоятельный проверяемый сценарий. Все 100 сценариев вместе с исходными тестами прошли проверку; отдельно проверялся каждый добавляемый тест в соответствующей версии кода. Названия и состав изменений приведены ниже. Номер соответствует методу `test_NNN` в `tests/test_prepared_regressions.py`.

## Публикация

Каждый московский календарный день для каждого репозитория выбираются **от 1 до 4 публикаций** и соответствующее число разных часов в диапазоне 09:00–22:59. В выбранный час запуск дополнительно смещается на случайное число секунд: номинально публикация начинается между :07 и :17. Часы и секунды меняются по дням и отличаются между репозиториями. План воспроизводится из даты и имени репозитория, поэтому повторные запуски не меняют дневную норму.

Workflow проверяет план раз в час с 09:07 до 22:07 по Москве; в невыбранные часы он завершается без изменения файлов. В выбранный час ожидается запланированное время (не более 10 минут), обновляется main и выполняется следующий патч с тестами. После 23:00 автоматическая публикация запрещена, в том числе если GitHub задержал запуск. Время самого коммита дополнительно зависит от длительности проверок. Ручные публикации также расходуют дневной лимит, а `check_only` его не расходует. Уже обработанный час повторно не используется.

GitHub Actions может задерживать запуски и пропускать их при высокой нагрузке; пропущенные шаги не догоняются массово. Поэтому 1–4 — выбранный план на день, а при сбое фактических публикаций может оказаться меньше. Исходные коммиты перечислены в таблице ниже; номер применённого шага сохраняется в состоянии очереди.

Перед публикацией проверяются хеш патча, родитель, название и список файлов, затем выполняется полный набор тестов проекта. Ошибка тестов, конфликт, изменение рабочей копии или отказ push прерывают запуск. Принудительная отправка и автоматическое разрешение конфликтов не используются. После 100 шагов новых коммитов не будет.

Очередь: `.ghostcommit/queue.json`; состояние: `.ghostcommit/state.json`; исполнитель: `scripts/publish_prepared.py`. Изменять счётчик вручную нельзя — порядок зависит от предыдущих патчей. Текущая ветка `main` может содержать пользовательские изменения: если они конфликтуют с очередью, потребуется вручную проверить и пересобрать оставшиеся патчи.

Для ручной проверки откройте **Actions → Проверенные изменения по расписанию → Run workflow**. Флажок `check_only` проверяет следующий патч без публикации. Без флажка применяется один шаг с тестами. Локально `python scripts/publish_prepared.py --check-only` только проверяет; команда без флага создаёт и отправляет коммит, поэтому её следует запускать в отдельной чистой копии.

Для остановки выберите **Disable workflow** в меню Actions. Токены в коде и локальной панели отсутствуют: workflow использует временный `GITHUB_TOKEN` с правом `contents: write`. Публикация через этот токен не запускает другие workflows на push, поэтому тесты выполняются непосредственно перед отправкой. Дополнительный PAT не требуется.

Защита очереди проверяется командой `python -m unittest discover -s .ghostcommit -p test_queue_worker.py -q`. Тесты используют временные локальные репозитории, без обращений к GitHub.

## Состав очереди

| № | Изменение | Исходный коммит |
|---|---|---|
| 1 | Поддержка часовых поясов в Windows | [a2954b2](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/a2954b2bd274d1a43e96db17056a58387c14a961) |
| 2 | Тест повторной регистрации пользователя | [deb547c](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/deb547c27349c5146273692eb2257f0f08eea4ad) |
| 3 | Обновление имени пользователя | [590e4d3](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/590e4d30822019b9dbfcdef97193af7ce5fb131a) |
| 4 | Сохранение даты первой регистрации | [37e6823](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/37e6823dfa7d967685c1be1463d6de649cd07e19) |
| 5 | Кириллица в профиле участника | [6e35229](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6e352296bf0d4b02426e70fc53f1b92fb25e041c) |
| 6 | Изоляция профилей участников | [9d57258](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/9d57258c3b00aa8414d175c64c4e5a68d5293de3) |
| 7 | Тест большого идентификатора MAX | [e25939b](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/e25939bd17a6da75198a8c9cdb1c9ca8c835cba3) |
| 8 | Подсчёт новых пользователей за день | [13a5f28](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/13a5f288d1008ccd13780242561a71f686ba8de3) |
| 9 | Подсчёт зарегистрированных пользователей | [9f443a8](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/9f443a8998e81e97a2c5e5f3b97350bfd8ad2a90) |
| 10 | Создание каталога для базы | [b3ce828](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/b3ce828581ff521ea3adda50550d3314f2f311cd) |
| 11 | Чтение профиля после открытия базы заново | [0713d59](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/0713d595c6e0799e709e916f9f47f22700754fd0) |
| 12 | Откат изменений при ошибке транзакции | [92c7746](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/92c77460c6d0ecb0048bbb93957969f6936ad356) |
| 13 | Поиск партнёра по дате акции | [a05e2f2](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/a05e2f296ed6ff5700c4bd824d570abd9581fbee) |
| 14 | День без партнёра в расписании | [c0eede1](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/c0eede1c4c96cb343df7ae8d0d0139970692db16) |
| 15 | Запрет двух партнёров на один день | [745f7e9](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/745f7e91f72b5da0eb66274b443efcd32ae79002) |
| 16 | Проверка уникальности партнёра | [e5c6bd2](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/e5c6bd2b5d57a5ae934a7d164adb4935b663c5ad) |
| 17 | Проверка числа победителей | [a784c33](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/a784c33dfa7674b43f1b406f7cb77273234993e0) |
| 18 | Проверка срока получения приза | [532fd2d](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/532fd2decc66df6170d402ff8056e07367d52cf8) |
| 19 | Срок получения приза по умолчанию | [77011a7](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/77011a7843d86978c87fa06ab19f72f308ea853c) |
| 20 | Порядок партнёров в статистике | [227c101](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/227c101f8bde4d5eae3c5312f328a4183f1205f9) |
| 21 | Импорт кодов неизвестного партнёра | [4e71c51](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/4e71c51ed5bb0d0cb89ee7d8a220598d986a5b5c) |
| 22 | Удаление пробелов при импорте кодов | [f95bb86](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f95bb867b17dad14e9926dc677d89e69a4deac98) |
| 23 | Пропуск пустых промокодов | [3813bbe](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/3813bbeaacd5445135c16ff4e59619c26d900316) |
| 24 | Повторный импорт без дубликатов | [e6cbe05](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/e6cbe05ecb3800bcd3fca2132c157caeb66760e7) |
| 25 | Одинаковые коды у разных партнёров | [8bbbc9e](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/8bbbc9e890940b75cb8b11f91f553cdff86c2e47) |
| 26 | Порядок выдачи промокодов | [73d2123](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/73d2123f62a190e88980213f00862425e83df83c) |
| 27 | Один промокод не выдаётся двум участникам | [9c87055](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/9c87055bde9e8b284010776c9202ed5441cbfbf5) |
| 28 | Повторная выдача уже назначенного кода | [c10ecde](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/c10ecde3972f8ae89696bf20f224c1a1fb6f45f5) |
| 29 | Повторный запрос не расходует запас кодов | [d97ec9c](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/d97ec9cbed36292545a9bb75bdaa54bc6e84be74) |
| 30 | Подсчёт обращений за промокодом | [964f22b](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/964f22bbf4df608a256efc314c60920325067ef9) |
| 31 | Нет шанса за запрос при пустом запасе | [44e2d6f](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/44e2d6fe4ad0d6dcaffc3e8ba4163784c1fac573) |
| 32 | Запрос кода несуществующего партнёра | [1ce36e3](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/1ce36e301d77fe7486d03a55349a17464c32875d) |
| 33 | Запрос кода незарегистрированным участником | [f162eab](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f162eab91e42f09f123941843c0df5a1bb2ab4a7) |
| 34 | Исправлен подсчёт оставшихся промокодов | [0bf0a67](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/0bf0a67d7168fed7152e361284adff0c140922d9) |
| 35 | Сохранение времени выдачи промокода | [5ab3a25](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/5ab3a25128ffc6b0c31a2e6196b64eb8bcd25230) |
| 36 | Тест повторной регистрации участия | [f80e900](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f80e900a1ec384d138669944f6b57d057495752c) |
| 37 | Проверка участия в нужной акции | [f233490](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f23349021b8552c64feb551a44dedb49887052f8) |
| 38 | Один шанс за два действия в один день | [9f6a4a1](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/9f6a4a1086d2fee93d6adc9af15aa849cda5a478) |
| 39 | Партнёр не дублируется в прогрессе | [b50e778](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/b50e778d89ef19a889ba3a4f71d19de80733014c) |
| 40 | Прогресс нового участника | [19df056](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/19df05656077f19e358548d5a813fc9127b02185) |
| 41 | Ограничение числа накопленных шансов | [f7d9038](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f7d90380a862ee82e84ca981551dd184ca1fded8) |
| 42 | Изоляция прогресса участников | [6bc0373](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6bc0373ca4a6b392f1a89ef9cd9fa597bf20c06b) |
| 43 | Порядок дней в прогрессе | [1036d36](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/1036d36c7fcfb463825eef73431c5d7bfaa0c109) |
| 44 | Промокод не заменяет регистрацию в розыгрыше | [4cf2057](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/4cf20579c8cbf4e02694b8d99545af0880935aaa) |
| 45 | Участие незарегистрированного пользователя | [7b8a205](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/7b8a20561f2fdac8f152370966c6af372e26874f) |
| 46 | Розыгрыш без участников | [0f85d2d](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/0f85d2d24ab45b7f30005f9adc1c8be1b0fb7224) |
| 47 | Победителей не больше числа участников | [1c45e4d](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/1c45e4dc99e07585dc81b5f945a548f4df983f88) |
| 48 | Победитель не попадает в резерв | [2eba701](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/2eba7011f148ca5a6772c6149c197b7d06933fa8) |
| 49 | Уведомления только после подтверждения итогов | [f5ab480](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f5ab480a8cd75115cc895e760e6a044121dd0f2d) |
| 50 | Запрет повторного розыгрыша дня | [f33465f](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f33465f5a4bbf47c38d63c817ade4dae5cb22112) |
| 51 | Розыгрыш в день без партнёра | [4eb4d56](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/4eb4d566e5f0c878b0927624b6dbc8c1cebdaed6) |
| 52 | Повторное подтверждение итогов | [e70337e](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/e70337e91e384b361f406796f66810e1f3d42db5) |
| 53 | Подтверждение несуществующего розыгрыша | [41451c0](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/41451c06da13a501b904e61fd529de9b8a880e50) |
| 54 | Запрос неизвестного розыгрыша | [41ee138](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/41ee138afe24172d225129928393ded77b19ac7c) |
| 55 | Сохранение подтверждённого статуса | [ed0dc78](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/ed0dc784ea6c2a89c7208a66a8100d71c3f0a1dd) |
| 56 | Финальный розыгрыш без участников | [c62d1f7](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/c62d1f7cedc893682cc2b99d8c1e43cea52fafa8) |
| 57 | Запрет повторного финального розыгрыша | [518d2ea](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/518d2ea9d2acee723cd648a994005499e81ab1ff) |
| 58 | Получатели промокодов в финальном розыгрыше | [b21ce20](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/b21ce2045f83827b80e8ba53980539f5d02f3674) |
| 59 | Список участников в протоколе | [63706d9](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/63706d997979a8289db82e2f7f24253113be8e80) |
| 60 | Размер пула при взвешенном выборе | [6b52abb](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6b52abb844b2ce380eb6416d1ae3e4419d754182) |
| 61 | Запрет изменения чужой заявки на приз | [20b723a](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/20b723a879714c77cf33903f2069fcf72f6df7e6) |
| 62 | Сбор имени после срока заявки | [cb3a7e1](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/cb3a7e153d932777670d993e70173e0d725ccb89) |
| 63 | Согласие без заполненного имени | [f853709](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f853709e8175178de0c9c5c3d7b5702851807079) |
| 64 | Сохранение отказа от передачи данных | [44e82f5](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/44e82f5342031e0e41ebe7e44d84728920b41d8f) |
| 65 | Очистка состояния после согласия | [4884ed8](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/4884ed884749baf4736f89086f013baeebc35396) |
| 66 | Исправлена проверка срока согласия на приз | [7018fdf](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/7018fdff2500206148ae5b539671bc0f3ccbd281) |
| 67 | Повторное согласие по закрытой заявке | [062ce86](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/062ce86da1c3b5a17889f2c06285ddef772f23fb) |
| 68 | Победитель не заменяется до дедлайна | [8777800](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/877780027f2006f8141f0c38d9591191d29e8528) |
| 69 | Подтверждённый победитель остаётся в списке | [3a33c11](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/3a33c11fc5e8cc128e1868cf0772f00bed4f8206) |
| 70 | Повторный обход просроченных заявок | [5156d2d](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/5156d2dfe56ba1d4f74f2536c356791b8de566d3) |
| 71 | Массовая рассылка зарегистрированным участникам | [59e6100](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/59e6100705ee50f4b5f69f3b4ebe560c9ae14bde) |
| 72 | Персональная рассылка одному участнику | [cea671e](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/cea671e03cbfcf506c5d3ab0aa8a17416d75282b) |
| 73 | Рассылка неизвестному адресату | [0afd9b9](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/0afd9b982fd8fb7274cd27a99b3617e037959d5b) |
| 74 | Ограничение выборки уведомлений | [b738dde](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/b738dde75d8a25af9b78ced68b74cfef16f1402e) |
| 75 | Отправленное уведомление не возвращается в очередь | [f989553](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f989553f06fb1ad32163bac15d3083adc8a6bf2a) |
| 76 | Сохранение ошибки доставки | [366bf22](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/366bf2209161a5b26ccbb6b8ca79ba122112f73c) |
| 77 | Ограничение длины ошибки доставки | [6094307](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6094307852ccc8da147ee653b0e047bacb29a6a2) |
| 78 | Порядок отправки уведомлений | [e8cb144](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/e8cb14424a5a6ae8c00a9c93495ed10d93500bc2) |
| 79 | Кириллица в состоянии диалога | [dc51de8](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/dc51de8a171a2bfdbc3c1bc61634a56ba8f04712) |
| 80 | Обновление состояния без дубликатов | [6119c3a](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6119c3ac3458a31eb7715d882b1454019693473c) |
| 81 | Нормализация адреса MAX API | [fb8de2a](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/fb8de2af5532c054d84f3d4b61ff441a0079183e) |
| 82 | Авторизация MAX через заголовок | [a03c050](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/a03c050138c92d5577a896d4daec40c535d90f65) |
| 83 | Тест нулевого маркера обновлений | [0a61748](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/0a61748aed0bb2495a0987d8849c54f09f444f7c) |
| 84 | Запрос обновлений без маркера | [b1441b7](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/b1441b7937f7d2aaaf62ca06560c6a0fe076d9c6) |
| 85 | Таймаут long polling | [6bbf6e3](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6bbf6e33479cce0dc5e9203ce0d70efe9c6afcdd) |
| 86 | Проверка подписки нужного участника | [76095b8](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/76095b8eb310346a4a151ee4d9488c0e1b2b5744) |
| 87 | Пустой список подписчиков | [0ca91c0](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/0ca91c0206a33a1ed930b6754e60ed5369ef88e7) |
| 88 | Тихая отправка сообщения | [6b26c19](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6b26c19ebce42fd58f2cdec8ae578ac4b64cf5a3) |
| 89 | Сообщение без пустых вложений | [ad50718](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/ad507188a8f414554af470fe02597d25768324aa) |
| 90 | Баннер и кнопки в одном сообщении | [ed36317](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/ed36317945b5c64c5dfcb036760698749694e270) |
| 91 | Клавиатура в ответе на callback | [bcadb38](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/bcadb382bf13ff3c3dfdb021f87eab7914c2ea76) |
| 92 | Обработка ошибки HTTP от MAX | [727705f](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/727705fc96270e67b497f126ffd6dfd758923a39) |
| 93 | Обработка сетевого таймаута MAX | [0b534ae](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/0b534ae0c5c3b5dd50a71ddc9a658d64e023eebb) |
| 94 | Обработка повреждённого JSON от MAX | [1a9d532](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/1a9d5321dbd30ea59b21cfb9700473a6b8160067) |
| 95 | Ограничение текста ошибки MAX | [f2ef99f](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/f2ef99fc07edfe3772a5310732cfcfb1acd80df9) |
| 96 | Переменные окружения важнее env-файла | [1b5f1b2](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/1b5f1b2ff4c5088a1081741fb2ccc1fc5d2230bb) |
| 97 | Знак равенства в значении env | [e8821e9](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/e8821e9c36cf44c7670ef30d48411808985b2d38) |
| 98 | Комментарии и пустые строки в env | [2bacc10](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/2bacc10267b8e6eba94bf4110de28173236f5678) |
| 99 | Кавычки в значениях env | [8d90599](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/8d905999208cea2306b01325dfcbbfe221c189a4) |
| 100 | Запуск без необязательного env-файла | [6a56e19](https://github.com/akiooooo/MAX-Giveaway-Bot/commit/6a56e1936854d987ad3bca294b02be7be76a5fef) |
