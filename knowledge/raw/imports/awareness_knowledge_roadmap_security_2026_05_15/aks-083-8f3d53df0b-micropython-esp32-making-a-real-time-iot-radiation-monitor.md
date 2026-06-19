# MicroPython & ESP32: Making a Real-Time IoT Radiation Monitor

**Published:** 2026-05-08


## How Often Do You Use Uranium to Debug Your Code?


![Image](https://miro.medium.com/v2/resize:fit:700/1*o3TD-cuLiLW6Cy_SR0KBSA.png)

*ESP32 and the Geiger-Müller tube, Image by author*

_If you don’t have a Medium account, a_ [_video version_](https://youtu.be/zD66ahC971w) _is available on YouTube._

Radiation is everywhere; the background radiation is always around us. With an 8$ ESP32 board, 3$ OLED screen, MicroPython, and a Geiger-Müller tube, we can easily create a radiation detector. It will allow us not only to see the radiation level but also to upload the data to GMCMap, Home Assistant, or other services. As a bonus, at the end of the article, I will show several **fun scientific experiments**, like detecting the radon gas in your house with only a vacuum cleaner and a sock.

Before we begin, a small note. This article took **more than 2 weeks** to prepare. And it included not only coding but also having real hardware and doing real experiments with various radiation sources. Does it make sense in the time of AI-slop, while some authors publish 2 stories per day? I don’t know. Write your thoughts in the comments below if you want. At least I hope that readers still appreciate real people doing real things.

And now, let’s get started! For those readers who would like to see the process “in action,” the video is added at the end of the article.

### 1\. Hardware

Obviously, it is not a purely Python project — to detect the radiation, we will need some hardware. The connection diagram is straightforward:

![Image](https://miro.medium.com/v2/resize:fit:700/1*5p5t2VvWYdbLPvKvKnqFNA.png)

*Image by author*

All components here are not expensive. As we can see, the largest part of the circuit is a Geiger counter kit board, which can be obtained on Amazon for about $50. Here, a **Geiger–Müller tube** is detecting the radioactive particles. When a particle is detected, the board generates a low-voltage pulse that can be processed by the **ESP32**. The ESP32 board also has Wi-Fi capabilities, and the data can be uploaded to the public GMCMap or any other service, like Home Assistant. Last but not least, we can also see the data on the **OLED screen**, which will allow us to do some fun experiments.

All components can be placed on a breadboard, and no soldering is required. This Geiger-Müller kit is pretty reliable, and for me, it was working 24/7 for about 6 months on a balcony. I used it with a Raspberry Pi to analyse radiation patterns and cosmic rays, and it was working well; you can find the link at the end of the article. But here, I will focus on the ESP32. And if you have never used MicroPython and ESP32, I recommend reading this part first:

[

## IoT For Beginners: Gentle Introduction To The ESP32

### Let’s Start With MicroPython and Arduino IDE

levelup.gitconnected.com


](/iot-for-beginners-gentle-introduction-to-the-esp32-43f5552b514e?source=post_page-----e08a46221b8a---------------------------------------)

And when the hardware is ready, we can start coding in Python.

### 2\. Coding

**2.1 Detecting Particles  
**Every radiation detector is capable of detecting individual particles — you probably heard the classical “clicks” of the Geiger counter. When the charged particle flies through the Geiger-Müller tube, the low-pressure gas becomes ionized, and you hear the “click” from the speaker. Our first task will be to **count these clicks**.

As a reminder, the radiation detector output is connected to the GPIO18 pin. Let’s initialize the pin as an input:

from machine import Pin  


geiger\_input = Pin(18, Pin.IN, None)

The third parameter here is important. The Geiger counter board already has an internal pull-up resistor, and we need to set the ESP32 pull-up to None; otherwise, the pulses will not be detected.

Now, we can use **an interrupt** to detect the pulses:

geiger\_input\_bounce\_ms = 2  
total\_pulses = 0  
last\_trigger\_time = 0  


def geiger\_input\_isr(pin: Pin):  
    """This function runs instantly when the input is triggered."""  
    global total\_pulses, last\_trigger\_time  
  
    \# Get the current time in milliseconds  
    current\_time = time.ticks\_ms()  
      
    \# Debounce: only count if 2ms have passed since the last valid press  
    if time.ticks\_diff(current\_time, last\_trigger\_time) > geiger\_input\_bounce\_ms:  
        total\_pulses += 1  
        last\_trigger\_time = current\_time  


geiger\_input.irq(trigger=Pin.IRQ\_FALLING, handler=geiger\_input\_isr)

As we can see, the logic here is simple, but there is a trick. In the ideal world, the interrupt will be triggered when a pin state changes from high to low (I use _Pin.IRQ\_FALLING_). However, because of the electromagnetic noise, the pulse shape is not perfect. In my case, for every particle, the interrupt was triggered twice.

The solution is simple, and it is called **debouncing**. I simply ignore the interrupt if it happened less than 2ms after the last one. Practically, the Geiger-Müller tube generates 10–30 counts per minute for the background radiation, and maybe up to 1,000–3,000 counts per minute for a highly radioactive source. So, the 2ms debouncing time is okay for us.

**2.2 CPM and CPS  
**At this moment, we can count the particles detected by the Geiger-Müller tube. However, practically, it is not useful yet, because all GM tubes are usually calibrated in **counts per minute**, or CPM.

In theory, we can wait for a minute and show the number of particles at the end of the interval. The first radiation detectors worked like this. They were often built on pure logic, like AND/OR gates and counters. They also had a “reset” button, which restarted the calculation. Nowadays, we want better functionality, and to show values in real-time, it is more convenient to calculate CPS, or **counts per second**.

Calculating the CPS is easy. I need to save the last updated time, and if more than a second has passed, a new value can be calculated. As a reminder, the pin interrupt is saving the counts in a _total\_pulses_ variable:

total\_pulses = 0  
last\_pulse\_count = 0  
last\_second\_time = time.ticks\_ms()  
uptime\_seconds = 0  
screen\_needs\_update = False  
  
def calculate\_cps():  
    """Get the new CPS value."""  
    global total\_pulses, last\_second\_time, last\_pulse\_count  
    global screen\_needs\_update  
  
    current\_time = time.ticks\_ms()  
    if time.ticks\_diff(current\_time, last\_second\_time) >= 1000:  
         pulses\_this\_sec = total\_pulses - last\_pulse\_count  \# Our new CPS  
         last\_pulse\_count = total\_pulses  
  
         last\_second\_time = current\_time   
         uptime\_seconds += 1  
         screen\_needs\_update = True  

Now, we can add this method to our main loop:

while True:  
    calculate\_cpm()  
  
    \# Redraw the screen when a new data is available  
    if screen\_needs\_update:  
        update\_display()              
        screen\_needs\_update = False  
  
    time.sleep\_ms(50)

We can make the calculation slightly more accurate by using a 1-second hardware timer. For simplicity reasons, this implementation is good enough.

Now, every second, a new CPS value will be calculated. To know the number of counts per minute, I will keep the historical data in a list:

HISTORY\_LENGTH = 600  
  
cps\_history = \[0\] \* HISTORY\_LENGTH

Here, I keep the values for the last 10 minutes, and it will also be useful for the GMCMap upload. When the new CPS value is ready, we just add it to a list:

cps\_history.pop(0)  
cps\_history.append(pulses\_this\_sec)

With the list of historical data, calculating the CPM from CPS is easy:

\# Calculate the CPM  
if uptime\_seconds < 60:  
    \# Extrapolate and sum only the recorded seconds  
    current\_sum = sum(cps\_history\[-uptime\_seconds:\])  
    cpm\_value = int((current\_sum / uptime\_seconds) \* 60)  
else:  
    \# Get the last 60 seconds  
    cpm\_value = sum(cps\_history\[-60:\])

As we can see, we have one edge case. If the board started less than a minute ago, we use approximation, and the values may not be so accurate during the first 10–20 seconds.

**2.3 OLED Screen  
**Our radiation detector is almost ready — it’s time to display the data on the screen. For that, I will use an I2C [SSD1306](https://docs.micropython.org/en/latest/esp8266/tutorial/ssd1306.html) MicroPython library:

import ssd1306  
from machine import SoftI2C  
  
oled\_width: int = 128  
oled\_height: int = 64  
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))  
oled = ssd1306.SSD1306\_I2C(oled\_width, oled\_height, i2c)  


def update\_display():  
    """Redraw the UI with the current data."""  
    oled.fill(0)  
      
    \# Calculate dose in microsieverts per hour  
    usv\_h = calculate\_usv\_value(cpm\_value)  
      
    \# Draw: left  
    cpm\_str = f"CPM:{cpm\_value}"  
    oled.text(cpm\_str, 0, 0)  
       
    \# Draw: right-alignment, 8px per char  
    usv\_str = f"{usv\_h:.2f}uSv"     
    usv\_x\_pos = oled\_width - (len(usv\_str) \* 8)  
    oled.text(usv\_str, usv\_x\_pos, 0)  
      
    \# Bottom graph for a last minute   
    draw\_cps\_graph(oled, cps\_history\[-60:\], 4, 20, 120, 43)  
      
    oled.show()

Here, we have several interesting parts. A _cpm\_value_ was already calculated before. It can be useful to compare the radiation level with the background. A **radiation dose** can be calculated from the CPM, according to the type of the Geiger-Müller tube:

def calculate\_usv\_value(cpm: int) -> float:  
    """Calculate uSv value from CPM. Constant depends on the GM tube model.  
    Some popular Geiger-Müller tubes:  
    SBM-20   0.0057  
    SBM-19   0.0021  
    SI-29BG  0.0082  
    SI-180G  0.0031  
    LND-712  0.0081  
    J305     0.0081  
    SBT11-A  0.0031  
    SBT-9    0.0117  
    """  
    return cpm\_value \* 0.0057

The OLED screen is small, and I will only show the last-minute data. Drawing the graph is easy because we have all the CPS values:

def draw\_cps\_graph(display: ssd1306.SSD1306\_I2C, data: list, x: int, y: int, width: int, height: int):  
    """Draws an auto-scaling bar graph of the CPS history."""  
    max\_val = max(data)  
    for i, val in enumerate(data):  
        bar\_height = int((val / max\_val) \* height)  
          
        px = x + (i \* 2)  
        py = y + height - bar\_height  
          
        display.fill\_rect(px, py, 2, bar\_height, 1)

Obviously, there is no Print Screen button on the ESP32 to take a screenshot, but this photo can give an idea. Here, I placed a uranium glass jar near the GM tube, and we can see the increase in the radiation level:

![Image](https://miro.medium.com/v2/resize:fit:700/1*lyrY12VKIrs28qhmeuSgSA.png)

*Image by author*

**2.4 Large Font Mode  
**Our detector works well and can already be used as a measurement tool. However, the screen is small, and we can easily make it more readable by using a larger font. This task is straightforward for a web developer. However, ESP32 has no OS and no preinstalled scalable fonts. Instead, I will use a [micropython-font-to-py](https://github.com/peterhinch/micropython-font-to-py) library.

Let’s say I want to show the value in microsieverts on a screen. First, I need to convert the existing font to a MicroPython file by running a command:

python3 font\_to\_py.py Roboto-Bold.ttf 24 font\_big.py -c 1234567890.

Here, 24 is the font size, and “123456789.” is our character set — the ESP32 flash memory is usually limited to 2–4 MB, and there is no need to convert characters we don’t need. As an output, a _font\_big.py_ file will be created. Inside, it looks like this:

\_font =\\  
b'\\x0b\\x00\\x1f\\x00\\x7f\\x80\\x7b\\xc0\\x71\\xc0\\x01\\xc0\\x01\\xc0\\x03\\x80'\\  
b'\\x07\\x80\\x0e\\x00\\x0e\\x00\\x0e\\x00\\x00\\x00\\x00\\x00\\x0e\\x00\\x1e\\x00'  
...  
  
\_index =\\  
b'\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x22\\x00\\x44\\x00'

Now, we can use this font in Python:

from writer import Writer  
import font\_big  


writer\_big = Writer(oled, font\_big)  
  
def update\_display\_large\_font():  
    """Big Text Mode: Show dose and status only."""  
    usv\_h = calculate\_usv\_value(cpm\_value)  
    usv\_str = "{:.2f}".format(usv\_h)  
  
    \# Draw radiation dose (Roboto 24px), centered  
    text\_width = writer\_big.stringlen(usv\_str)  
    dose\_x = (oled\_width - text\_width) // 2  
    Writer.set\_textpos(oled, col=dose\_x, row=10)   
    writer\_big.printstring(usv\_str)  
  
    \# Draw status level (Roboto 16px): LOW, MEDIUM, or HIGH, centered  
    status\_str = get\_dose\_rate(usv\_h)  
    text\_width = writer\_medium.stringlen(status\_str)  
    status\_x = (oled\_width - text\_width) // 2  
    Writer.set\_textpos(oled, col=status\_x, row=40)  
    writer\_medium.printstring(status\_str)  
  
    oled.show()

Now everyone knows about microsieverts, and I also added a _get\_dose\_rate_ method to show the value in an easy-readable format:

def get\_dose\_rate(usv: float) -> str:  
    """Categorizes the radiation level based on uSv/h."""  
    if usv < 0.25:  
        return "LOW"  
    elif usv < 1.0:  
        return "MEDIUM"  
    else:  
        return "HIGH"

The output looks like this:

![Image](https://miro.medium.com/v2/resize:fit:700/1*ipgQus6gTT-l3AWRlp5mgA.png)

*Image by author*

Both modes can be useful. If you want to analyse the radiation level of a specific object, like a vintage clock or uranium glass, a CPS graph is more informative. If you want to have a radiation monitoring and see a level in a room or in a basement, a large font is more readable.

### 3\. GMCMap Upload

Our detector is now fully functional. As a last step before doing some experiments, let's connect the ESP32 to a Wi-Fi and upload the data to a public [GMCMap](https://www.gmcmap.com). The website looks like this:

![Image](https://miro.medium.com/v2/resize:fit:700/1*h9UktVb672vjlIz-nqUG6w.png)

*Screenshot by author*

The service is completely free, and it is supported by volunteers. And we can easily upload our data as well with an ESP32 — let’s do it.

First, we need to create an account on the [GMCMap](https://www.gmcmap.com) website and get the account ID and the Geiger counter ID. And obviously, to upload the data, we will need the Wi-Fi credentials:

WIFI\_SSID = ""  
WIFI\_PASS = ""  
  
GMC\_AID = "xxxxx"       \# GMCMap Account ID  
GMC\_GID = "xxxxxxxxxx"  \# GMCMap Geiger Counter ID  
GMC\_UPLOAD\_INTERVAL\_MS = 2\*60\_000

First, let’s connect the ESP32 board to the **Wi-Fi**:

import network  
  
wlan = network.WLAN(network.STA\_IF)  
  
def connect\_wifi():  
    """Connects to the local Wi-Fi network."""  
    wlan.active(True)  
      
    if not wlan.isconnected():  
        wlan.connect(WIFI\_SSID, WIFI\_PASS)  
        \# Wait until connected  
        while not wlan.isconnected():  
            time.sleep(0.5)  

Now, let’s make a method to **upload the data**:

def upload\_to\_gmcmap():  
    """Uploads the current CPM and uSv data to GMCmap."""  
    if not wlan.isconnected():  
        \# Reconnect if needed, data will be sent during the next call  
        wlan.connect(WIFI\_SSID, WIFI\_PASS)  
        return  
      
    global cpm\_value  
      
    \# Recalculate values for the upload  
    usv\_h = calculate\_usv\_value(cpm\_value)  
    cpm\_avg = calculate\_average\_cpm(minutes=5)  
         
    try:  
        \# Build the URL string  
        url = f"http://www.GMCmap.com/log2.asp?AID={GMC\_AID}&GID={GMC\_GID}&CPM={cpm\_value}&ACPM={cpm\_avg}&uSV={usv\_h:.4f}"  
        \# Send the HTTP GET request  
        response = urequests.get(url)  
        response.close()  
    except Exception as exc:  
        print(f"Upload failed: {exc}")

As we can see, the data is sent via the simple GET (yes, it’s _GET_, not _POST_) request. And there is also no _https_ — the API was originally made for GMC Geiger counters, which often have a simple microcontroller and a limited computing power.

Now, we can call this method from the main loop. The GMCMap server accepts the data only every 2–5 minutes, so we need to keep the last upload time:

last\_upload\_time = time.ticks\_ms()  
  
while True:  
    calculate\_cpm()  
      
    \# Redraw screen every second  
    if screen\_needs\_update:  
        update\_display()  
        screen\_needs\_update = False  
          
    \# Send data to GMCMap  
    current\_time = time.ticks\_ms()  
    if time.ticks\_diff(current\_time, last\_upload\_time) >= GMC\_UPLOAD\_INTERVAL\_MS:  
        upload\_to\_gmcmap()  
        last\_upload\_time = current\_time

Now, we can run the board and see the data, which may look like this:

![Image](https://miro.medium.com/v2/resize:fit:700/1*PA1lI-pue_QLUbJViS8Veg.png)

*Someone’s GMCMap station, Screenshot by author*

The GMCMap server is public, and after installing the detector, we can see its radiation level from everywhere in the world. And it can also help others to see the radiation data. It’s rare, but sometimes anomalies happen. Once, I saw a substantial increase in the background radiation level, which was ~1.5-2x of normal for several hours. It was probably caused by the solar activity — at least I hope that it was not a radiological incident, and there was nothing in the news or SMS alerts that day.

Congratulations to readers, patient enough to get up to this point! Our coding part is done, and we are ready to make several fun experiments.

### 4\. Experiments

Now, let’s see the radiation detector in action. Here, I will show three experiments that, despite their simplicity, can provide interesting results.

**4.1 Background Radiation**  
Our first experiment is simple: we can just do nothing and observe the graph on the screen:

![Image](https://miro.medium.com/v2/resize:fit:700/1*EPaP5UnZiSd5l2ZuhBRMPA.png)

*Image by author*

What we see is called the **background radiation**. And here, the results are interesting.

*   The background radiation is always around us, and it's never zero. The SMB-20 tube in my detector gets about 20 particles per minute, and as we can guess, thousands or maybe even millions of radioactive particles are flying through our bodies every minute. The radiation is called **ionizing** because it has enough energy to destroy the atoms and create ions. However, cells in our bodies have efficient internal mechanisms of self-repair. Practically, only a radiation dose of 100 millisieverts (100,000 microsieverts) statistically increases the risk of cancer.
*   Radioactive decay is truly random, unlike pseudo-random generators used in programming languages. With a small update of the code, you can easily make a scientifically proven random number or random password generator — I will keep it as homework for the viewers.
*   You can take the radiation detector to the airplane (though I would advise first making a better case for it, not to confuse the airport security;) and see that the radiation level during the flight is ~10x higher compared to the ground level because of cosmic rays.

**4.2 Beta and Gamma Radiation**  
On the detector screen, we can see the number of detected particles. However, the radioactive particles themselves are not all the same.

*   Alpha particles are a stream of helium nuclei. They can be emitted by some sources, like americium, or by some minerals like uraninite. Alpha particles have a lot of energy but low penetrating power; they can be easily stopped even by a piece of paper.
*   Beta radiation is mostly a stream of high-speed electrons. They have higher penetrating power, but can be stopped by a relatively dense object, such as aluminium or even plastic.
*   Gamma radiation is a stream of high-energy photons. It is practically light, but in the very high and invisible spectrum range. High-energy photons can go through the paper and through the plastic — gamma radiation can only be stopped by lead or a thick layer of water or concrete.

A Geiger-Müller tube, used in this test, is not capable of detecting alpha particles. However, we can easily distinguish between beta and gamma radiation. As a second experiment, I am taking the jar covered with the uranium glaze. It is a relatively strong beta emitter, and it also emits some gamma. Now, I am covering the jar with a plastic transport card:

![Image](https://miro.medium.com/v2/resize:fit:700/1*ElLJN0iJkfZ1ExTLEwjhQg.png)

*Image by author*

The result is interesting. Though we cannot see the electrons with our eyes, we can clearly see the ~50% reduction of the radiation level on the graph. Which means that about half of the radiation emitted by the jar is beta, and another half is gamma.

**4.3 Detecting the Radon Gas**  
The third experiment is interesting, and it is also practically useful. And it is a bit scary. Radon is a radioactive gas that is naturally emitted by rocks or soil. It can be present in almost every house, and it was calculated that radon is the second leading cause of lung cancer after smoking.

The third experiment is simple, though the results can be scary. You take a sock, put it on a vacuum cleaner pipe, and leave it running for about 10 minutes, so the air is going through the pipe and the sock:

![Image](https://miro.medium.com/v2/resize:fit:700/1*3FmE8x1FPSUmsD_G6V22kA.png)

*Image by author*

After that, you take the sock and put it on a Geiger-Müller tube. Highly likely, you will see an increase in the radiation level! To verify that it is not a mistake, I took a more sensitive GMC detector, which shows that after 5 minutes os sucking the air, the sock got a 3.5x of the background radiation level:

![Image](https://miro.medium.com/v2/resize:fit:700/1*M2itc8tq-_wvjlDyrQ0Asg.png)

*Image by author*

What is going on here? We can see the **decay products of radon**, which include polonium, lead, and other elements. Which can be scary because all this happens in the air and also in our lungs! However, this is already far from Python coding and a bit off-topic for this article. More details can be found in the video at the end of the story.

### Conclusion

In this article, I explained how to make an ESP32 radiation detector almost from scratch and how to code it in MicroPython, and we also did some useful experiments. If you also want to see the process “in action,” you are welcome to watch the video:

Video by author

If you enjoyed this story, press a “Like” button — it helps me to know if particular topics are interesting to readers or not. If you want to see more stories, use the “Follow” or “Subscribe” buttons, and you will get a notification when the next article is published. The full source code for this article is available on my [Patreon page](https://www.patreon.com/deliuseev) — your support may help me to get more hardware like this for testing.

If you’re interested in Python and scientific data processing, you may also be interested in reading other articles:

[

## Budget Spectroscopy With Python, OpenCV, and Matplotlib

### Fun Experiments With Python and a USB Spectrometer

levelup.gitconnected.com


](/optical-spectroscopy-in-python-opencv-and-matplotlib-64c6074443ab?source=post_page-----e08a46221b8a---------------------------------------)

[

## Processing Astronomical Images with Python and OpenCV

### Let’s Look Deep Into Space

python.plainenglish.io


](https://python.plainenglish.io/processing-astronomical-images-with-python-and-opencv-38c45ef33819?source=post_page-----e08a46221b8a---------------------------------------)

[

## Exploratory Data Analysis: Radiation Monitoring with Python and Geiger Counter

### Collecting and Processing of the Geiger–Müller Tube Data

medium.com


](https://medium.com/data-science-collective/exploratory-data-analysis-radiation-monitoring-with-python-and-geiger-counter-c5a6bf4c05a6?source=post_page-----e08a46221b8a---------------------------------------)

Thanks for reading.