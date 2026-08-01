# Hardware Setup Guide

This guide provides instructions for setting up the OLED display and status LED module for the Honeypot Kit.

## Required Components

- Raspberry Pi (3B+, 4, or newer)
- OLED display module (128x64 resolution, I2C interface)
- LED traffic light module (red, yellow, green LEDs with built-in resistors)
- Breadboard and jumper wires

## Wiring Diagram

TBD with images

## OLED Display Setup

1. Connect the OLED display to the Raspberry Pi following the wiring diagram.
2. Install the necessary Python libraries:
```bash
   pip install adafruit-circuitpython-ssd1306
```
3. Run the `oled_display.py` script to start displaying honeypot status information.

## Status LED Module Setup

1. Connect the LED traffic light module to the Raspberry Pi following the wiring diagram.
2. Update the (TBD) `led_control.py` script to use the appropriate GPIO pins for the red, yellow, and green LEDs.
3. Run the updated (TBD) `led_control.py` script to start indicating honeypot status with the LED colors.

## Customization

You can customize the behavior of the OLED display and LED module by modifying the (TBD) `hardware_config.ini` file. See the comments in that file for available options.

## Troubleshooting

- **OLED display is blank:** Check your wiring and make sure the I2C interface is enabled on your Raspberry Pi.
- **LEDs aren't lighting up:** Check your wiring and ensure you've connected the correct GPIO pins for each color.

If you encounter any other issues or have questions, please open an issue on the GitHub repository.
