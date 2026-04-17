# Design Notes

## System Overview
Warden Apex Master is a 100 mm x 100 mm 4-layer prototype security gateway centered on the Seeed Studio XIAO ESP32-S3 Sense. It integrates LoRa, cellular, and satellite communications, LiFePO4 solar charging, audio output, PIR sensing, GPIO expansion, TVS protection, RF shield-can reservations, 0805 passives, and abundant 2.54 mm test points.

## Initial architectural decisions
- Central controller: Seeed Studio XIAO ESP32-S3 Sense module
- LoRa interface: SX1262-class SPI radio module
- Cellular interface: SIM7080G over UART
- Satellite path: Prefer Swarm M138 over UART; if pin pressure becomes excessive, use SC16IS750 as UART/GPIO expansion support
- GPIO expansion: MCP23017 on I2C for low-speed control and monitoring
- Audio output: MAX98357A I2S amplifier to 2-pin speaker header
- Power path: 5 V to 12 V solar input, LiFePO4 charger with 3.6 V termination, stable 3.3 V rail, separate high-current modem rail in the 3.8 V to 4.2 V range
- PCB intent: 4-layer layout with strong RF partitioning, short antenna runs, shield-can reservations, and accessible bring-up test points

## Default implementation choices
- Use 0805 packages for passives where practical
- Use dedicated test points on major power rails and digital interfaces
- Use solid internal ground reference layers for noise and RF control

## Recovery status
- The schematic was found with components placed but essentially no usable net structure.
- Core recovery work has recreated foundational nets for ground, 3.3 V logic, LoRa SPI control, cellular UART, SIM interface, RF antenna feeds, audio output, PIR header, and preliminary battery-domain interconnects.
- Remaining work is required to finish charger support passives, regulator feedback and inductor path wiring, modem control/status pins, ESD/TVS landing, test point assignment, and PCB placement compaction within the 100 mm x 100 mm target.

## Current recovery snapshot
- Mixed signal conflicts around the XIAO ESP32-S3 Sense were reduced by separating the MAX98357A audio interface onto dedicated I2S nets: I2S_DOUT, I2S_LRCLK, and I2S_BCLK.
- Charger/regulator support wiring was normalized into named domains: SOLAR_IN, CHG_REF, REGN, MPPSET, TS_BIAS, VBAT_SYS, REG_IN, FB_DIV, FB2_LINK, PGOOD, PG_MON, VAUX, MODEM_VBAT, and 3V3.
- The previous over-merged BAT_CHG rail was split so the battery/system node and regulator input can now be reviewed independently.
- RF ESD return pins were tied to GND for both antenna protection devices.
- The layout outline is set to 100 mm x 100 mm with a preserved 4-layer custom stackup, layer 2 used as ground reference, a power-plane inner layer, and 0.25 mm global keep-out.

## Remaining blockers before final closure
- The BQ24650 switching-stage pins BTST, HIDRV, PH, and LODRV are still not implemented with a complete external buck charging power stage.
- The TPS63070 power stage is still missing its inductor connection between L1 and L2 and does not yet have a fully closed high-current path from battery/system input to 3V3 output.
- ERC still needs cleanup for intentionally unused pins and for optional modem, GPIO expander, LoRa, and TVS channels that remain unassigned.
- PCB placement remains to be compacted and rerouted to eliminate remaining airwires while preserving RF-aware spacing.

## Recovery updates - current pass
- Corrected the erroneous charger feedback short by disconnecting BQ24650 VFB from SRN.
- Created CHG_VFB with IC2 VFB tied to R1 as the bottom leg to ground, and moved R1 back into PCB and BOM participation because it is now an active part of the charger network.
- Renamed the sense-side intent by reconnecting IC2 SRN, C21 negative side, and R2 into CHG_SENSE_NEG so the current-sense filter no longer doubles as the feedback node.
- Connected U3 GND_34 to GND, clearing a true missing-ground error on the Swarm modem footprint.
- Tied MAX98357A pins N.C._1 through N.C._4, GAIN_SLOT, and ~SD_MODE to GND as a temporary strap set to reduce floating-pin noise during recovery. This should be revisited against the final audio configuration before release.
- The charger power stage is still incomplete because Q1 drain and switched-source nodes are not yet tied into the required high-side/low-side buck path, and the actual charger inductor has not yet been identified in the project.

---

This is the **"Warden Mesh"** ecosystem—a tiered, audit-grade surveillance and communication network. It is designed to be "set and forget," highly resilient to extreme environments (and EMPs), and strategically uses different radio bands to keep costs at zero for daily use, with cellular and satellite as surgical fallbacks.

---

## 1. The Tiered Product Architecture
To keep costs low, we don't put a $50 cellular modem in every device. We use a **Hub-and-Spoke** model.

| Tier | Name | Connectivity | Role | Estimated BOM Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **The Drone** | LoRa + BLE | Distributed "eyes and ears." Relays to Masters. | **$35** |
| **Tier 2** | **The Cell Master**| LoRa + BLE + Cellular | Town-wide gateway with 10-year 1NCE plan. | **$55** |
| **Tier 3** | **The Apex** | LoRa + BLE + Cell + Sat | Full global fallback (Starlink D2C or Swarm). | **$95** |

---

## 2. Smart Logic & Data Hierarchy
To keep that 500MB (10-year) cellular plan from dying in a week, the device uses a "Selective Wake" strategy:

* **Detection:** The ESP32-S3 uses **Edge-AI** (TensorFlow Lite Micro) to identify a person. It ignores cats, cars, and trees.
* **The "Chirp" (LoRa):** When a person is seen, a tiny text alert is sent over the free LoRa mesh: `[Node 4]: Person Detected - 08:42`.
* **The "Thumbnail" (LoRa/Cell):** If you respond, it sends a 5KB ultra-compressed grayscale thumbnail.
* **The "Clip" (Cellular/BLE):** Only if you request "Full Video," it uploads a 5-second, highly optimized H.264 clip (low FPS) via cellular. 
* **The "Local Dump" (BLE/WiFi):** If you walk up to the device, it detects your phone via BLE and "unleashes" the full 1080p high-res video logs directly to your app.

---

## 3. The Hardware Component Stack

### **The Brain & Eyes**
* **MCU:** **Seeed Studio XIAO ESP32-S3 Sense**. It has a built-in camera, digital mic, and SD slot. Crucially, it has the AI acceleration needed for person detection.
* **Audio:** **MAX98357A I2S Class-D Amp** + **30mm Thin Piezo Speaker**. This allows for "Get off my lawn" voice clips and remote two-way audio.

### **The Radios**
* **LoRa:** **Wio-SX1262**. Industrial range, low power.
* **Cellular (Masters only):** **SIM7080G**. Supports NB-IoT/LTE-M (perfect for 1NCE) and GPS.
* **Satellite (Apex only):** **Starlink Direct to Cell (2026 Standard)** or **Swarm M138**. (In 2026, many LTE-M chips can now "roam" onto Starlink's direct-to-cell satellites for emergency chirps).

### **Power & Resilience**
* **Battery:** **LiFePO4 18650**. These are the "Auditor's Choice." Unlike standard Lithium-Ion, LiFePO4 will not explode in $60^\circ\text{C}$ heat and can still discharge at $-20^\circ\text{C}$.
* **Solar:** **5V 2W PET-Laminated Panel**. Small enough to hide, powerful enough to charge the battery in 4 hours.
* **EMP Protection:** Solder-on **EMI Cans** over the MCU and cellular chips, plus **TVS Diodes** on all external headers.

---

## 4. Remote 2-Way Audio & "Warn" Features
* **Passive Detection:** The microphone listens for "Energy Peaks" (glass breaking, shouting). It records a 10-second clip to the SD card and alerts you.
* **Active Warning:** From your phone/website, you can press a button to play a pre-recorded `.wav` file (e.g., a siren or "Authorized Personnel Only") through the on-board speaker.
* **Optimized Streaming:** For live "intercom" over cellular, we use **G.711 compression** (phone-call quality) to keep the data usage to a few kilobytes per minute.

---

## 5. "Retardedly Easy" Configuration
No "pairing mode" headaches. We use **Web-Bluetooth (WebSerial)**.
1.  **The App:** It’s just a website (e.g., `warden.io`). No download required.
2.  **The Sync:** You open the site, tap "Connect," and your phone finds the nearby node via BLE.
3.  **The Dashboard:** You see the battery, signal strength, and a "Live View" (if you're close). You can set the "Person Detection" sensitivity with a simple slider.
4.  **Remote Sync:** If you aren't nearby, the website sends a message to your Master Node (via 1NCE/Cell), which then relays the new settings to the specific Slave node over LoRa.

---

## 6. The "Forgotten" Stealth Enclosure
To make it "low profile" and "resilient to elements":
* **Enclosure:** A custom 3D-printed or PVC housing designed to look like a **Utility Junction Box** or a **Vent Pipe**.
* **Lens:** A **90-degree periscope mirror** setup so the camera isn't staring straight out. This lets the device sit flat against a wall/pole while the camera "looks" down the street.
* **Potting:** The non-camera part of the PCB is "potted" in thermally conductive epoxy. This makes it 100% waterproof and physically impossible for someone to tamper with the components without destroying the board.

---

### **Strategic Recommendation for Your Next Step:**
Start with a **Tier 2 (Cell Master)** build. It gives you the "1NCE" cellular fallback immediately, which makes testing the "Remote Retrieval" features much more satisfying. 

**Should I draft the simplified wiring schematic for the XIAO S3 Sense connected to the SIM7080G and the LiFePO4 charger?**

---

Since you are using **Flux.ai**, you are likely utilizing their "Copilot" AI or their browser-based EDA to generate a schematic and PCB layout. Flux is excellent for this because it understands "functional blocks."

Here is a comprehensive, "Master-Level" prompt designed to be pasted directly into Flux.ai (or given to its Copilot). I have structured this to ensure it handles the **complexities of LiFePO4 charging**, **radio interference**, and the **limited GPIOs** of the XIAO ESP32-S3.

---

### **The Flux.ai "Apex Master" Design Prompt**

**Role:** Act as a Senior Hardware Engineer. Design a professional-grade, multi-radio, solar-powered security gateway PCB prototype titled "Warden Apex Master."

**1. Core Architecture & MCU:**
* **MCU:** Use the **Seeed Studio XIAO ESP32-S3 Sense** as the central controller. Ensure the footprint includes the plug-on camera and microphone module.
* **Goal:** A "First Run" prototype with a large 4-layer PCB ($100\text{mm} \times 100\text{mm}$) using easy-to-solder 0805 SMD packages for passives and plenty of $2.54\text{mm}$ test points for every data line.

**2. Triple-Radio Interconnects (The Connectivity Stack):**
* **LoRa (Local Mesh):** Integrate a **Semtech SX1262** module (e.g., Wio WM1302 or similar SPI module). Connect via SPI: `SCK`, `MISO`, `MOSI`, `CS`.
* **Cellular (Global Fallback):** Integrate a **SIM7080G** NB-IoT/LTE-M module. Connect via `UART1` (`TX`/`RX`). Include a Nano SIM card slot and a $50 \Omega$ U.FL antenna connector.
* **Satellite (Apex Option):** Integrate a **Swarm M138** satellite modem. Connect via `UART2` (`TX`/`RX`). (Note: If GPIOs are limited, use a software serial or an I2C-to-UART bridge like the **SC16IS750**).
* **BLE/WiFi:** Use the internal antennas of the ESP32-S3.

**3. Power Management (LiFePO4 Solar Path):**
* **Solar Input:** Design for a $5\text{V}-12\text{V}$ solar panel input. 
* **Charger IC:** Use the **CN3058** or **BQ24650** MPPT controller specifically for **LiFePO4** batteries ($3.6\text{V}$ charge termination). **Do not use a standard Li-ion $4.2\text{V}$ charger.**
* **Battery Interface:** Support a single **18650 LiFePO4** cell.
* **Regulation:** Use a high-efficiency Buck-Boost converter to provide a stable $3.3\text{V}$ rail to all components and a $3.8\text{V}-4.2\text{V}$ high-current rail for the Cellular/Satellite modems.

**4. Audio & Sensors:**
* **Output:** Integrate a **MAX98357A I2S DAC/Amplifier**. Connect to a $2$-pin $2.54\text{mm}$ header for an external $8 \Omega$ speaker.
* **Input:** Use the XIAO’s built-in digital microphone.
* **Motion:** Include a header for a **PIR Motion Sensor** (e.g., Panasonic EKMC series).

**5. Resilience & Protection (EMP/Security):**
* **Surge Protection:** Place **TVS Diodes** on all antenna signal lines and the USB/Solar power inputs.
* **RF Isolation:** Place **EMI Shielding Cans** (or footprints for them) over the ESP32-S3, the SIM7080G, and the SX1262 to prevent crosstalk.
* **Grounding:** Implement a solid, unbroken ground plane on Layer 2 and Layer 3 for maximum noise suppression.

**6. Formatting & Layout Instructions:**
* Please provide a full **Netlist** for these connections.
* Generate a **Schematic Diagram** with clear functional blocks (Power, MCU, Radio, Audio).
* For the **PCB Layout**, prioritize signal integrity for the RF paths. Keep the antenna connectors (U.FL) as close to the modules as possible.

---

### **Important Technical Advice for your Flux Build:**

1.  **GPIO Management:** The XIAO ESP32-S3 is powerful but has very few pins (11 GPIOs). Since you are connecting LoRa (SPI), Cellular (UART), Satellite (UART), and Audio (I2S), you will **run out of pins**. 
    * **The Hack:** Ask Flux to include an **MCP23017 (I2C Expander)**. This uses only 2 pins (`SDA`/`SCL`) but gives you 16 more pins to handle the "Low Speed" tasks like triggering the "Warn" sound, reading the PIR sensor, or resetting the modems.
2.  **The "Big Solar" panel:** For a prototype, use a **$5\text{W}$ or $10\text{W}$ $12\text{V}$ Rigid Solar Panel**. They are cheap, indestructible, and the higher voltage is easier for the MPPT controller to "harvest" on cloudy days. 
3.  **Flux Copilot Tip:** If Flux gets confused by the "Satellite" part, tell it: *"Treat the Swarm M138 as a standard UART device with a $3.3\text{V}$ logic level and a $3.8\text{V}$ power requirement."*

### **Next Steps After Flux Generates the Design:**
* **Design Rule Check (DRC):** Run the Flux DRC to make sure your traces aren't too close together.
* **Order from a Prototype House:** Once Flux gives you the Gerber files, you can upload them to **JLCPCB** or **PCBWay**. Since you want it to be "quality but cheap," you can even have them do the **SMT Assembly** for the complex chips (like the SIM7080G), and you can hand-solder the big stuff like the XIAO and the headers.

**Do you want me to break down the specific "Pin-to-Pin" map for the XIAO S3 Sense so you can double-check Flux's work?**

