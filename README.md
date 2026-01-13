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
  {% if states('sensor.loe_power_off') in ['unknown', 'unavailable', None, {}] %}
  ### Графік вимкнень недоступний
  
  {% else %}
  
  ### Графік вимкнень ([{{ strptime(state_attr('sensor.loe_power_off', 'day'), '%d.%m.%Y').strftime('%d-%m-%Y') }}](https://poweron.loe.lviv.ua))
  
  {% set now_dt = now() %}  
  {% set now_ts = now_dt.timestamp() %}
  {% set schedule = state_attr('sensor.loe_power_off', 'schedule') %}
  
  {% if schedule not in ['unknown', 'unavailable', None, {}] %}
    {% set sorted_days = schedule | dictsort(by='key') %}
    {% for day, intervals in sorted_days %}
      {# hide past days #} 
      {% if strptime(day, '%d.%m.%Y').date() < now_dt.date() %} 
        {% continue %}
      {% endif %} 
  **{{ day }}**
      {% if intervals %}
        {% for interval in intervals %}
          {# parse start datetime, handle 24:00 #}
          {% if interval[0] == '24:00' %} 
            {% set start_dt = strptime(day ~ ' 00:00', '%d.%m.%Y %H:%M') + timedelta(days=1) %} 
          {% else %} 
            {% set start_dt = strptime(day ~ ' ' ~ interval[0], '%d.%m.%Y %H:%M') %} 
          {% endif %}
  
          {# parse end datetime, handle 24:00 #} 
          {% if interval[1] == '24:00' %} 
            {% set end_dt = strptime(day ~ ' 00:00', '%d.%m.%Y %H:%M') + timedelta(days=1) %} 
          {% else %} 
            {% set end_dt = strptime(day ~ ' ' ~ interval[1], '%d.%m.%Y %H:%M') %} 
          {% endif %} 
              
          {% if end_dt.timestamp() < now_ts %} 
            {# past interval #} 
  - ~~{{ interval[0] }} – {{ interval[1] }}~~
          {% elif start_dt.timestamp() <= now_ts <= end_dt.timestamp() %} 
            {# current interval #} 
  - {{ interval[0] }} – {{ interval[1] }} (now)
          {% else %} 
            {# future interval #} 
  - {{ interval[0] }} – {{ interval[1] }}
          {% endif %} 
        {% endfor %}
      {% else %}
  Є електроенергія
      {% endif %}
    {% endfor %}
  {% else %}
  Дані недоступні
  {% endif %}
  
  <small>Оновлено {{ strptime(state_attr('sensor.loe_power_off', 'updated'), '%Y-%m-%dT%H:%M:%S').strftime('%H:%M %d-%m') }}/{{ strptime(state_attr('sensor.loe_power_off', 'updated_at')[0:19], '%Y-%m-%dT%H:%M:%S').strftime('%H:%M %d-%m') }}</small>

  {% endif %}
```

---

```
python3 -m venv ~/work/bk_loe_power_off/venv
source ~/work/bk_loe_power_off/venv/bin/activate
```
