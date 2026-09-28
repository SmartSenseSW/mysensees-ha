# MySense Home Assistant Integration – Implementation Spec

## Goal

Build a **Home Assistant custom integration** for MySense air quality devices using the cloud API.

The integration must:

* Authenticate using username + password
* Fetch device data from API
* Create sensor entities for all available measurements
* Follow Home Assistant best practices (async, coordinator pattern, config flow)

---

## API Details

### Base URL

`https://<YOUR_API_DOMAIN>`

### Authentication

* Method: username + password
* Endpoint: `/login`
* Response contains token (Bearer)

### Main Data Endpoint

`GET /api/v2/config/gateway/{gatewayId}`

Returns:

* Device metadata
* Device state (wifi, uptime, etc.)
* Sensor data inside `things[]`

Each `thing` contains:

* `type` → sensor type (T, RH, CO2, PM2.5, etc.)
* `lastMeasurement.v` → value
* `lastMeasurement.ts` → timestamp

---

## Integration Requirements

### 1. Architecture

Use Home Assistant standard structure:

```
custom_components/mysense/
  __init__.py
  manifest.json
  const.py
  config_flow.py
  coordinator.py
  sensor.py
  api.py
```

Use:

* `DataUpdateCoordinator` for polling
* `aiohttp` for async HTTP
* `config_flow` for UI setup

---

### 2. Config Flow

User must input:

* username
* password
* gateway_id

Flow must:

* authenticate
* fetch gateway data
* fail with proper errors:

  * invalid_auth
  * cannot_connect

Use gateway name as title if available:

```
editable.name
```

---

### 3. API Client

Implement:

* async_login()
* async_get_gateway(gateway_id)

Requirements:

* store bearer token
* retry once on 401
* raise custom exceptions:

  * AuthError
  * ApiError

---

### 4. Data Coordinator

* Poll every 120 seconds
* Fetch full gateway JSON
* Store raw response in `coordinator.data`

---

### 5. Sensors

Create dynamic sensors based on `things[]`

#### Mapping:

| Type  | Name        | Unit  |
| ----- | ----------- | ----- |
| T     | Temperature | °C    |
| RH    | Humidity    | %     |
| P     | Pressure    | kPa   |
| CO2   | CO2         | ppm   |
| PM1   | PM1         | µg/m³ |
| PM2.5 | PM2.5       | µg/m³ |
| PM10  | PM10        | µg/m³ |

Rules:

* Use `lastMeasurement.v` as value
* Use proper Home Assistant device classes where possible
* Use `SensorStateClass.MEASUREMENT`

---

### 6. Diagnostic Sensors

From:
`state.deviceState`

Add:

* wifiRSSI → signal strength
* uptime → seconds
* LDSR → last seen timestamp

Mark as:

```
entity_category = diagnostic
```

---

### 7. Device Info

Device must include:

* name → editable.name
* model → inventory.hw_ver
* firmware → inventory.sw_ver
* serial → inventory["S/N"]
* identifier → gateway id

---

### 8. Entity Design Rules

* One Home Assistant device per gateway
* One entity per sensor type
* Unique ID format:

```
{gateway_id}_{sensor_type}
```

---

### 9. Error Handling

* API down → mark entities unavailable
* Auth failure → require reauth later (future improvement)
* Timeout handling required

---

### 10. Manifest

Must include:

```json
{
  "domain": "mysensees",
  "name": "MySensees",
  "version": "0.1.0",
  "config_flow": true,
  "iot_class": "cloud_polling"
}
```

---

## Nice-to-Have (Optional)

If time permits:

* Options flow (change scan interval)
* Support multiple gateways
* Logging for debugging
* Diagnostics endpoint dump

---

## Acceptance Criteria

Integration is complete when:

* Can be added via UI
* Successfully authenticates
* Creates sensors for all `things`
* Updates values every 2 minutes
* Appears correctly under Devices & Entities

---

## Notes

* Follow Home Assistant async patterns strictly
* Do NOT use blocking requests
* Keep code clean and modular
* Avoid hardcoding sensor types beyond mapping table
* Everything must work with real API responses

---
