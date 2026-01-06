# BK LOE Power Off

A Home Assistant Integration for LOE PowerOn site - [https://poweron.loe.lviv.ua/](https://poweron.loe.lviv.ua/).

Reads data from the webapp API.

## Install

### Installation via HACS

Have [HACS](https://hacs.xyz/) installed, this will allow you to update easily.

* Adding BK LOE Power Off to HACS 
[https://my.home-assistant.io/redirect/hacs_repository/?owner=bkhrupa&repository=bk_loe_power_off&category=integration](https://my.home-assistant.io/redirect/hacs_repository/?owner=bkhrupa&repository=bk_loe_power_off&category=integration)


If the link above does not work, add `https://github.com/bkhrupa/bk_loe_power_off` as a custom repository of type Integration in HACS.

* Click Install on the `BK LOE Power Off` integration.
* Restart the Home Assistant.

Manual installation
 
* Copy `bk_loe_power_off`  folder from [latest release](https://github.com/bkhrupa/bk_loe_power_off/releases/latest) to [`custom_components` folder](https://developers.home-assistant.io/docs/creating_integration_file_structure/#where-home-assistant-looks-for-integrations) in your config directory.
* Restart the Home Assistant.

## Example markdown card

```
type: markdown
content: |
  ### Графік вимкнень ([{{ strptime(state_attr('sensor.loe_power_off', 'day'), '%d.%m.%Y').strftime('%d-%m-%Y') }}](https://poweron.loe.lviv.ua))
  
  {% set raw = states('sensor.loe_power_off') %}

  {% if raw not in ['unknown', 'unavailable', None, ''] %}
    {% set json_str = raw | replace("'", '"') %}
    {% set intervals = json_str | from_json %}

    {% if intervals %}
      {% for interval in intervals %}
  - {{ interval[0] }} - {{ interval[1] }}
      {% endfor %}
    {% else %}
  Є електроенергія
    {% endif %}
  {% else %}
  Дані недоступні
  {% endif %}
  
  <small>Оновлено {{ strptime(state_attr('sensor.loe_power_off', 'updated'), '%Y-%m-%dT%H:%M:%S').strftime('%H:%M %d-%m-%Y') }}/{{ strptime(state_attr('sensor.loe_power_off', 'updated_at')[0:19], '%Y-%m-%dT%H:%M:%S').strftime('%H:%M %d-%m-%Y') }}</small>

```

---

```
python3 -m venv ~/work/bk_loe_power_off/venv
source ~/work/bk_loe_power_off/venv/bin/activate
```
