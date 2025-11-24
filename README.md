# BK LOE Power Off 

A Home Assistant Integration for LOE PowerOn site - [https://poweron.loe.lviv.ua/](https://poweron.loe.lviv.ua/).

Reads data from the webapp API.

## Example markdown card

```
- type: markdown
  content: >
    ### Графік вимкнень
    
    Оновлено {{ as_datetime(state_attr('sensor.loe_power_off', 'updated')) }}
    
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
 
```

---

```
python3 -m venv ~/work/bk_loe_power_off/venv
source ~/work/bk_loe_power_off/venv/bin/activate
```
