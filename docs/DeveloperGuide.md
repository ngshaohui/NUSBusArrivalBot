# NUSBusArrivalBot Developer Guide

## 1. Setting up

#### Prerequisites

1. **python3.6 or later**

#### Setting up the development environment

Use a virtual environment to set up an isolated working space. This ensures that you have the required distribution packages, and that they do not conflict with your existing ones.

1. Install the virtualenv distribution package
> `pip3 install virtualenv`

2. Set up the virtualenv
> `virtualenv dev`

3. Enter the virtualenv (**Windows**)
> `.\dev\Scripts\activate`

3. Enter the virtualenv (**Unix**)
> `./dev/lib/activate`

4. Install the required packages
> `pip3 install -r requirements.txt`

5. To leave the virtualenv
> `deactivate`