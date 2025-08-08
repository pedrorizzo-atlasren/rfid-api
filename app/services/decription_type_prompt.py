def description_type_prompt(product, manufacturer, technical_description, summary):
    return f"""
        Based on the following product and its information, determine the product's type and its technical description according to its type.

        Product's name: {product}; Porduct's manufacturer: {manufacturer}; product's technical description: {technical_description}; Summarry about the product: {summary}

        The type of the product can be ONLY HMI, UPS, accessory, actuator, adapter, air dryer, analyzer, antenna, antenna accessory, auxiliary contact, battery, battery module, busbar, bushing, 
        cabinet, cable, cable accessory, cable connector, cable insulation, capacitor, capacitor bank, capacitor board, chemical dispenser, chemical product, circuit breaker, circuit breaker accessory, 
        communication module, connector, contact accessory, contact block, contact relay, contactor, contactor accessory, contactor auxiliary contact, contactor coil, contactors, controller, cooling oil, 
        disconnector, display, drive, enclosure, fan, fan accessory, fastener, filter, fuse, fuse base, fuse holder, heater, indicator light, inductor, insulating oil, insulation, insulator, insulator chain, 
        inverter, inverter accessory, limit switch, lock, lubricant, measurement device, mechanical component (tracker), module, monitoring device, motor, mounting bracket, mounting rail, network converter, 
        network switch, packing set, panel, power module, power supply, reactor, rectifier, regulatory relay, relay, relay socket, relay timer, resistor, resistor card, seal kit, sensor, sensor amplifier, 
        sensor module, signage, solar panel, surge arrester, surge protector, switch, test block, timer, timer switch, tool set, tracker, transformer, transformer accessory, transformer monitor, unknown item, 
        valve, washer or phase module.

        If the product's type is HMI, return: {{
        "type": "HMI",
        "technical_description": {{
            "display type": "value",
            "screen size (inches)": "value",
            "resolution": "value",
            "interface": "value"
        }} 
        }},
        If the product's type is UPS, return: {{
        "type": "UPS",
        "technical_description": {{
            "input voltage (V)": "value",
            "output voltage (V)": "value",
            "battery type": "value",
            "backup time (min)": "value",
            "supply type (AC or DC)": "value",
            "rated capacity (kVA)": "value",
            "efficiency (%)": "value",
            "topology (online/offline)": "value",
            "transfer time (ms)": "value",
            "weight (kg)": "value"
        }}
        }},
        If the product's type is accessory, return: {{
        "type": "accessory",
        "technical_description": {{
            "accessory type": "value"
        }}
        }},
        If the product's type is actuator, return: {{
        "type": "actuator",
        "technical_description": {{
            "actuator type": "value"
        }}
        }},
        If the product's type is adapter, return: {{
        "type": "adapter",
        "technical_description": {{
            "input voltage (V)": "value",
            "output voltage (V)": "value",
            "connector type": "value",
            "power rating (W)": "value"
        }}
        }},
        If the product's type is air dryer, return: {{
        "type": "air dryer",
        "technical_description": {{
            "airflow (CFM)": "value",
            "operating pressure (bar)": "value",
            "power consumption (W)": "value"
        }}
        }},
        If the product's type is analyzer, return: {{
        "type": "analyzer",
        "technical_description": {{
            "measured parameters": "value",
            "input range": "value",
            "accuracy": "value",
            "display type": "value"
        }}
        }},
        If the product's type is antenna, return: {{
        "type": "antenna",
        "technical_description": {{
            "frequency range (MHz)": "value",
            "gain (dBi)": "value",
            "polarization": "value",
            "beamwidth (°)": "value",
            "connector type": "value"
        }}
        }},
        If the product's type is antenna accessory, return: {{
        "type": "antenna accessory",
        "technical_description": {{
            "accessory type": "value",
            "compatible antenna types": "value"
        }}
        }},
        If the product's type is auxiliary contact, return: {{
        "type": "auxiliary contact",
        "technical_description": {{
            "contact configuration": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is battery, return: {{
        "type": "battery",
        "technical_description": {{
            "nominal voltage (V)": "value",
            "capacity (Ah)": "value",
            "chemistry": "value",
            "cycle life (cycles)": "value",
            "weight (kg)": "value",
            "energy density (Wh/kg)": "value",
            "internal resistance (mΩ)": "value",
            "maximum discharge rate (C)": "value",
            "operating temperature range (°C)": "value",
            "self-discharge rate (%/month)": "value"
        }}
        }},
        If the product's type is battery module, return: {{
        "type": "battery module",
        "technical_description": {{
            "nominal voltage (V)": "value",
            "capacity (Ah)": "value",
            "chemistry": "value",
            "weight (kg)": "value"
        }}
        }},
        If the product's type is busbar, return: {{
        "type": "busbar",
        "technical_description": {{
            "cross-sectional area (mm²)": "value",
            "material": "value",
            "rated current (A)": "value"
        }}
        }},
        If the product's type is bushing, return: {{
        "type": "bushing",
        "technical_description": {{
            "voltage rating (kV)": "value"
        }}
        }},
        If the product's type is cabinet, return: {{
        "type": "cabinet",
        "technical_description": {{
            "material": "value",
            "degree of protection (IP/NEMA)": "value",
            "mounting style": "value"
        }}
        }},
        If the product's type is cable, return: {{
        "type": "cable",
        "technical_description": {{
            "cross-sectional area (mm²)": "value",
            "operating voltage (V)": "value",
            "conductor material": "value",
            "insulation material": "value",
            "temperature rating (°C)": "value",
            "outer diameter (mm)": "value"
        }}
        }},
        If the product's type is cable accessory, return: {{
        "type": "cable accessory",
        "technical_description": {{
            "accessory type": "value",
            "compatible cable types": "value"
        }}
        }},
        If the product's type is cable connector, return: {{
        "type": "cable connector",
        "technical_description": {{
            "compatible conductor cross-sectional area (mm²)": "value",
            "connection type": "value",
            "number of contacts": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is cable insulation, return: {{
        "type": "cable insulation",
        "technical_description": {{
            "insulation material": "value",
            "thickness (mm)": "value",
            "maximum temperature (°C)": "value",
            "dielectric strength (kV/mm)": "value"
        }}
        }},
        If the product's type is capacitor, return: {{
        "type": "capacitor",
        "technical_description": {{
            "capacitance (µF)": "value",
            "rated voltage (V)": "value",
            "tolerance (%)": "value",
            "dielectric type": "value",
            "ESR (Ω)": "value",
            "ripple current (A)": "value",
            "temperature coefficient (ppm/°C)": "value",
            "leakage current (µA)": "value",
            "operating temperature range (°C)": "value",
            "dimensions (mm)": "value"
        }}
        }},
        If the product's type is capacitor bank, return: {{
        "type": "capacitor bank",
        "technical_description": {{
            "total capacitance (µF)": "value",
            "rated voltage (V)": "value",
            "number of modules": "value"
        }}
        }},
        If the product's type is capacitor board, return: {{
        "type": "capacitor board",
        "technical_description": {{
            "board type": "value",
            "number of capacitor slots": "value",
            "mounting style": "value"
        }}
        }},
        If the product's type is chemical dispenser, return: {{
        "type": "chemical dispenser",
        "technical_description": {{
            "application": "value"
        }}
        }},
        If the product's type is chemical product, return: {{
        "type": "chemical product",
        "technical_description": {{
            "type of product": "value"
        }}
        }},
        If the product's type is circuit breaker, return: {{
        "type": "circuit breaker",
        "technical_description": {{
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "trip curve": "value",
            "number of poles": "value",
            "breaking capacity (kA)": "value"
        }}
        }},
        If the product's type is circuit breaker accessory, return: {{
        "type": "circuit breaker accessory",
        "technical_description": {{
            "accessory type": "value",
            "compatible circuit breakers": "value"
        }}
        }},
        If the product's type is communication module, return: {{
        "type": "communication module",
        "technical_description": {{
            "supported protocols": "value",
            "input voltage (V)": "value",
            "power consumption (W)": "value",
            "data rate (Mbps)": "value",
            "interface type": "value",
            "inputs": "value",
            "outputs": "value"
        }}
        }},
        If the product's type is connector, return: {{
        "type": "connector",
        "technical_description": {{
            "compatible conductor cross-sectional area (mm²)": "value",
            "connection type": "value",
            "number of contacts": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "contact material": "value",
            "termination style": "value"
        }}
        }},
        If the product's type is contact accessory, return: {{
        "type": "contact accessory",
        "technical_description": {{
            "compatible contactors": "value"
        }}
        }},
        If the product's type is contact block, return: {{
        "type": "contact block",
        "technical_description": {{
            "number of circuits": "value",
            "contact configuration": "value",
            "rated current (A)": "value"
        }}
        }},
        If the product's type is contact relay, return: {{
        "type": "contact relay",
        "technical_description": {{
            "coil voltage (V)": "value",
            "contact configuration": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is contactor, return: {{
        "type": "contactor",
        "technical_description": {{
            "coil voltage (V)": "value",
            "contact configuration": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "number of poles": "value",
            "utilization category (e.g. AC3)": "value",
            "mechanical life (operations)": "value",
            "electrical life (operations)": "value",
            "auxiliary contacts count": "value",
            "operating temperature range (°C)": "value"
        }}
        }},
        If the product's type is contactor accessory, return: {{
        "type": "contactor accessory",
        "technical_description": {{
            "compatible contactors": "value",
            "accessory type": "value"
        }}
        }},
        If the product's type is contactor auxiliary contact, return: {{
        "type": "contactor auxiliary contact",
        "technical_description": {{
            "contact configuration": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is contactor coil, return: {{
        "type": "contactor coil",
        "technical_description": {{
            "coil voltage (V)": "value",
            "power consumption (W)": "value"
        }}
        }},
        If the product's type is contactors, return: {{
        "type": "contactors",
        "technical_description": {{
            "coil voltage (V)": "value",
            "contact configuration": "value",
            "rated current (A)": "value"
        }}
        }},
        If the product's type is controller, return: {{
        "type": "controller",
        "technical_description": {{
            "type of controller": "value"
        }}
        }},
        If the product's type is cooling oil, return: {{
        "type": "cooling oil",
        "technical_description": {{
            "viscosity (cSt)": "value",
            "dielectric strength (kV)": "value",
            "flash point (°C)": "value",
            "pour point (°C)": "value",
            "density (kg/m³)": "value",
            "viscosity index (VI)": "value",
            "total acid number (TAN)": "value",
            "oxidation stability (hours)": "value"
        }}
        }},
        If the product's type is disconnector, return: {{
        "type": "disconnector",
        "technical_description": {{
            "rated voltage (V)": "value",
            "rated current (A)": "value",
            "number of poles": "value"
        }}
        }},
        If the product's type is display, return: {{
        "type": "display",
        "technical_description": {{
            "screen size (inches)": "value",
            "resolution": "value",
            "display type": "value",
            "interface": "value"
        }}
        }},
        If the product's type is drive, return: {{
        "type": "drive",
        "technical_description": {{
            "rated power (kW)": "value",
            "supply voltage (V)": "value",
            "control type": "value",
            "efficiency (%)": "value",
            "current rating (A)": "value",
            "frequency range (Hz)": "value",
            "overload capacity (e.g. % for x s)": "value",
            "cooling method": "value",
            "communication interface": "value"
        }}
        }},
        If the product's type is enclosure, return: {{
        "type": "enclosure",
        "technical_description": {{
            "enclousure application": "value"
        }}
        }},
        If the product's type is fan, return: {{
        "type": "fan",
        "technical_description": {{
            "power consumption (W)": "value",
            "voltage (V)": "value",
            "type of fan": "value"
        }}
        }},
        If the product's type is fan accessory, return: {{
        "type": "fan accessory",
        "technical_description": {{
            "accessory type": "value",
            "compatible fan models": "value"
        }}
        }},
        If the product's type is fastener, return: {{
        "type": "fastener",
        "technical_description": {{
            "type of fastener": "value"
        }}
        }},
        If the product's type is filter, return: {{
        "type": "filter",
        "technical_description": {{
            "type of filter": "value"
        }}
        }},
        If the product's type is fuse, return: {{
        "type": "fuse",
        "technical_description": {{
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "fuse type": "value",
            "breaking capacity (kA)": "value",
            "time characteristic": "value",
            "I²t (A²s)": "value",
            "voltage drop (V)": "value",
            "ambient temperature rating (°C)": "value",
            "dimensions (mm)": "value",
            "material": "value"
        }}
        }},
        If the product's type is fuse base, return: {{
        "type": "fuse base",
        "technical_description": {{
            "supported fuse type": "value",
            "mounting style": "value"
        }}
        }},
        If the product's type is fuse holder, return: {{
        "type": "fuse holder",
        "technical_description": {{
            "supported fuse size": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "number of poles": "value"
        }}
        }},
        If the product's type is heater, return: {{
        "type": "heater",
        "technical_description": {{
            "heating power (W)": "value",
            "supply voltage (V)": "value",
            "element type": "value",
            "enclosure rating": "value",
            "temperature range (°C)": "value",
            "control type (e.g. thermostat, PID)": "value",
            "heating element material": "value",
            "mounting style": "value"
        }}
        }},
        If the product's type is indicator light, return: {{
        "type": "indicator light",
        "technical_description": {{
            "voltage (V)": "value",
            "application": "value"
        }}
        }},
        If the product's type is inductor, return: {{
        "type": "inductor",
        "technical_description": {{
            "inductance (µH)": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "DC resistance (Ω)": "value",
            "self-resonant frequency (MHz)": "value"
        }}
        }},
        If the product's type is insulating oil, return: {{
        "type": "insulating oil",
        "technical_description": {{
            "viscosity (cSt)": "value",
            "dielectric strength (kV)": "value",
            "flash point (°C)": "value",
            "pour point (°C)": "value",
            "total acid number (TAN)": "value",
            "density (kg/m³)": "value"
        }}
        }},
        If the product's type is insulation, return: {{
        "type": "insulation",
        "technical_description": {{
            "insulation material": "value",
            "thickness (mm)": "value",
            "dielectric strength (kV/mm)": "value"
        }}
        }},
        If the product's type is insulator, return: {{
        "type": "insulator",
        "technical_description": {{
            "material": "value",
            "rated voltage (kV)": "value",
            "mechanical load (kN)": "value"
        }}
        }},
        If the product's type is insulator chain, return: {{
        "type": "insulator chain",
        "technical_description": {{
            "link material": "value",
            "link strength (kN)": "value",
            "link length (mm)": "value"
        }}
        }},
        If the product's type is inverter, return: {{
        "type": "inverter",
        "technical_description": {{
            "rated power (kW)": "value",
            "input voltage (V)": "value",
            "output voltage (V)": "value",
            "efficiency (%)": "value",
            "switching frequency (kHz)": "value",
            "total harmonic distortion (THD)": "value",
            "protection class (IP)": "value",
            "cooling method": "value"
        }}
        }},
        If the product's type is inverter accessory, return: {{
        "type": "inverter accessory",
        "technical_description": {{
            "type of accessory": "value",
            "compatible inverters": "value"
        }}
        }},
        If the product's type is limit switch, return: {{
        "type": "limit switch",
        "technical_description": {{
            "actuation type": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is lock, return: {{
        "type": "lock",
        "technical_description": {{
            "lock type": "value",
            "material": "value",
            "mounting style": "value"
        }}
        }},
        If the product's type is lubricant, return: {{
        "type": "lubricant",
        "technical_description": {{
            "viscosity (cSt)": "value",
            "temperature range (°C)": "value",
            "base oil type": "value",
            "viscosity index (VI)": "value",
            "pour point (°C)": "value",
            "flash point (°C)": "value",
            "additive package": "value",
            "density (kg/m³)": "value"
        }}
        }},
        If the product's type is measurement device, return: {{
        "type": "measurement device",
        "technical_description": {{
            "measured parameter": "value",
            "range": "value",
            "accuracy": "value",
            "resolution": "value"
        }}
        }},
        If the product's type is mechanical component (tracker), return: {{
        "type": "mechanical component (tracker)",
        "technical_description": {{
            "mechanical motion range (°)": "value",
            "load capacity (kg)": "value"
        }}
        }},
        If the product's type is module, return: {{
        "type": "module",
        "technical_description": {{
            "module type": "value",
            "input voltage (V)": "value",
            "power consumption (W)": "value"
        }}
        }},
        If the product's type is monitoring device, return: {{
        "type": "monitoring device",
        "technical_description": {{
            "application": "value"
        }}
        }},
        If the product's type is motor, return: {{
        "type": "motor",
        "technical_description": {{
            "power (kW)": "value",
            "voltage (V)": "value",
            "frequency (Hz)": "value",
            "speed (rpm)": "value",
            "number of poles": "value",
            "supply type (AC or DC)": "value",
            "efficiency (%)": "value",
            "enclosure type (IP rating)": "value"
        }}
        }},
        If the product's type is mounting bracket, return: {{
        "type": "mounting bracket",
        "technical_description": {{
            "application": "value"
        }}
        }},
        If the product's type is mounting rail, return: {{
        "type": "mounting rail",
        "technical_description": {{
            "rail type": "value"
        }}
        }},
        If the product's type is network converter, return: {{
        "type": "network converter",
        "technical_description": {{
            "number of ports": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is network switch, return: {{
        "type": "network switch",
        "technical_description": {{
            "number of ports": "value",
            "supported speeds": "value",
            "power consumption (W)": "value",
            "switching capacity (Gbps)": "value",
            "port types (RJ45/SFP)": "value",
            "PoE support": "value",
            "management interface": "value",
            "VLAN support": "value",
            "manageable (yes/no)": "value",
            "supported protocols (e.g. SNMP, STP, LACP)": "value",
            "dimensions (mm)": "value",
            "operating temperature range (°C)": "value"
        }}
        }},
        If the product's type is packing set, return: {{
        "type": "packing set",
        "technical_description": {{
            "number of items": "value",
            "item type": "value"
        }}
        }},
        If the product's type is panel, return: {{
        "type": "panel",
        "technical_description": {{
            "material": "value",
            "number of cells": "value",
            "finish": "value",
            "weight (kg)": "value"
        }}
        }},
        If the product's type is power module, return: {{
        "type": "power module",
        "technical_description": {{
            "rated power (kW)": "value",
            "input voltage (V)": "value",
            "output voltage (V)": "value"
        }}
        }},
        If the product's type is power supply, return: {{
        "type": "power supply",
        "technical_description": {{
            "output voltage (V)": "value",
            "output current (A)": "value",
            "input voltage range (V)": "value"
        }}
        }},
        If the product's type is reactor, return: {{
        "type": "reactor",
        "technical_description": {{
            "rated inductance (mH)": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is rectifier, return: {{
        "type": "rectifier",
        "technical_description": {{
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "number of phases": "value"
        }}
        }},
        If the product's type is regulatory relay, return: {{
        "type": "regulatory relay",
        "technical_description": {{
            "function type": "value",
            "coil voltage (V)": "value",
            "contact configuration": "value"
        }}
        }},
        If the product's type is relay, return: {{
        "type": "relay",
        "technical_description": {{
            "type": "value",
            "coil voltage (V)": "value",
            "contact configuration": "value",
            "contact material": "value",
            "rated current (A)": "value",
            "switching voltage (V)": "value"
        }}
        }},
        If the product's type is relay socket, return: {{
        "type": "relay socket",
        "technical_description": {{
            "compatible relays": "value",
            "mounting style": "value"
        }}
        }},
        If the product's type is relay timer, return: {{
        "type": "relay timer",
        "technical_description": {{
            "timing range": "value",
            "supply voltage (V)": "value",
            "timing accuracy": "value",
            "output type": "value"
        }}
        }},
        If the product's type is resistor, return: {{
        "type": "resistor",
        "technical_description": {{
            "resistance (Ω)": "value",
            "tolerance (%)": "value",
            "power rating (W)": "value",
            "material": "value"
        }}
        }},
        If the product's type is resistor card, return: {{
        "type": "resistor card",
        "technical_description": {{
            "number of resistors": "value",
            "card type": "value",
            "mounting style": "value"
        }}
        }},
        If the product's type is seal kit, return: {{
        "type": "seal kit",
        "technical_description": {{
            "kit contents": "value",
            "material compatibility": "value"
        }}
        }},
        If the product's type is sensor, return: {{
        "type": "sensor",
        "technical_description": {{
            "sensor type": "value",
            "measurement range": "value",
            "output signal": "value",
            "supply voltage (V)": "value"
        }}
        }},
        If the product's type is sensor amplifier, return: {{
        "type": "sensor amplifier",
        "technical_description": {{
            "gain": "value",
            "input range": "value",
            "bandwidth": "value"
        }}
        }},
        If the product's type is sensor module, return: {{
        "type": "sensor module",
        "technical_description": {{
            "sensor type": "value",
            "interface": "value",
            "supply voltage (V)": "value"
        }}
        }},
        If the product's type is signage, return: {{
        "type": "signage",
        "technical_description": {{
            "material": "value",
            "type of signage": "value"
        }}
        }},
        If the product's type is solar panel, return: {{
        "type": "solar panel",
        "technical_description": {{
            "maximum power (Wp)": "value",
            "voltage at max power (Vmp)": "value",
            "current at max power (Imp)": "value",
            "open-circuit voltage (Voc)": "value",
            "short-circuit current (Isc)": "value",
            "efficiency (%)": "value",
            "temperature coefficient (%/°C)": "value",
            "dimensions (mm)": "value",
            "weight (kg)": "value",
            "frame material": "value"
        }}
        }},
        If the product's type is surge arrester, return: {{
        "type": "surge arrester",
        "technical_description": {{
            "nominal discharge current (kA)": "value",
            "maximum continuous operating voltage (V)": "value",
            "number of poles": "value",
            "material": "value"
        }}
        }},
        If the product's type is surge protector, return: {{
        "type": "surge protector",
        "technical_description": {{
            "nominal discharge current (kA)": "value",
            "maximum continuous operating voltage (V)": "value"
        }}
        }},
        If the product's type is switch, return: {{
        "type": "switch",
        "technical_description": {{
            "switch type": "value",
            "rated current (A)": "value",
            "rated voltage (V)": "value",
            "actuator type": "value"
        }}
        }},
        If the product's type is test block, return: {{
        "type": "test block",
        "technical_description": {{
            "type": "value",
            "number of circuits": "value",
            "material": "value",
            "insulation rating": "value"
        }}
        }},
        If the product's type is timer, return: {{
        "type": "timer",
        "technical_description": {{
            "timing range": "value",
            "supply voltage (V)": "value",
            "timing accuracy": "value"
        }}
        }},
        If the product's type is timer switch, return: {{
        "type": "timer switch",
        "technical_description": {{
            "actuation type": "value",
            "timing range": "value",
            "rated voltage (V)": "value"
        }}
        }},
        If the product's type is tool set, return: {{
        "type": "tool set",
        "technical_description": {{
            "number of tools": "value",
            "tool types": "value"
        }}
        }},
        If the product's type is tracker, return: {{
        "type": "tracker",
        "technical_description": {{
            "tracking type": "value",
            "input voltage (V)": "value",
            "input current (A)": "value",
            "power consumption (W)": "value",
            "mechanical motion range (°)": "value"
        }}
        }},
        If the product's type is transformer, return: {{
        "type": "transformer",
        "technical_description": {{
            "rated power (kVA)": "value",
            "primary voltage (V)": "value",
            "secondary voltage (V)": "value",
            "frequency (Hz)": "value"
        }}
        }},
        If the product's type is transformer accessory, return: {{
        "type": "transformer accessory",
        "technical_description": {{
            "compatible transformers": "value",
            "accessory type": "value"
        }}
        }},
        If the product's type is transformer monitor, return: {{
        "type": "transformer monitor",
        "technical_description": {{
            "monitored parameters": "value",
            "interface": "value",
            "supply voltage (V)": "value"
        }}
        }},
        If the product's type is unknown item, return: {{
        "type": "unknown item",
        "technical_description": {{
            "application": "value"
        }}
        }},
        If the product's type is valve, return: {{
        "type": "valve",
        "technical_description": {{
            "valve type": "value",
            "material": "value",
            "pressure rating (bar)": "value"
        }}
        }},
        If the product's type is washer, return: {{
        "type": "washer",
        "technical_description": {{
            "washer type": "value",
            "material": "value",
            "dimensions (mm)": "value"
        }}
        }},
        If the product's type is phase module, return: {{
        "type": "phase module",
        "technical_description": {{
            "rated voltage (V)": "value",
            "rated current (A)": "value",
            "switching device type (e.g. IGBT, MOSFET)": "value",
            "cooling method (e.g. air, liquid)": "value",
            "dimensions (mm)": "value",
            "weight (kg)": "value"
        }}
        }}
        
        If any technical information is not found, answer the field with 'not found'. 
        
        For example, for a solar panel with all fields found: {{  
        "type": "solar panel",  
        "technical_description": {{ 
            "maximum power (Wp)": "400",  
            …  
        }}  
        }}.

        For a solar panel with some fields not found: {{  
        "type": "solar panel",  
        "technical_description": {{
            "maximum power (Wp)": "350",  
            …  
        }}  
        }}.
        """