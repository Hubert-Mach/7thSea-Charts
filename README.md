# 7th Sea Map Project

The goal of the project is to create framework for creating maps and to chart 7th Sea world.

## Assumptions

We are charting imaginary world. While effort is done to prevent as much as possible from original maps, don't get upset if something is gone. Feel free to create it.


## The World

As game is inspired by 17th century Europe. We can easily assume the world size is the same.

But this is lazy way. Lets do some investigation!

All maps have a 'scale' information - length and how many miles it is. This alone does not give us a chance to calculate world size.
The only map that has scale AND Longtitude and Latitude information is 'The Land od 1000 Nations'. Distance between 30 and 45 N degree mark is 272 mm. We have no idea what projection was used (if any) then let's make dirty calculation: 272mm/15 degrees => 1 degree = 18mm. 100 miles equals 25mm. This gives us 4 miles per mm. So we have 72 miles per 1 degree. Multiplying it by 360 we get 25920 Miles. Our earth have 21600 nautical miles of circumreference. This would mean that Terra is 20% bigger. But we also do not know what kind of miles are on map. If we assume that on map we have LAND MILES then our earth have 24901 land miles on equator. Quite close! Only 4% difference which can be measure error done at the very beginning. So what does it mean? It means that Terra is same size as Earth and maps have Land Mile yardstick on them.


## Project tools

- Wonderdraft for map edition
- Python scripts for basic automation 
- JavaScript for project display

## Resources

Wonderdtaft assets for 7th Sea are subset of brushes and fonts developed by K.M. Alexander (https://kmalexander.com/free-stuff/fantasy-map-brushes/)

## Project structure

- scripts - handy python scripts to start from scratch
- tiles/far - tiles rendered for global view
- tiles/near - tiles rendered for zoomed view

There are 32 far tiles and 2592 near tiles, plus 2 tiles for polar caps.

## Project setup

Clone repository to your computer.

If you are starting from scratch prepare ONE big map of the world. Make seas and oceans black and lands white. When ready run tile generation script from scripts directory

`python3 gen_tiles.py MAP_FILE.png`

This will cut image into tiles which are png and will put them into ../tiles_png directory.

If you want to see how it looks like already, run

`python3 compress_tiles.py ../tiles_png/far --out ../tiles/far --webp-quality 80 --no-png-fallback`

And start local web server

`python3 -m http.server 8000`

Check results visiting http:/localhost:8000


## Workflow

Start with far tiles. Open one and write down its dimensions. Create tiles_wonderdraft/far and tiles_wonderdraf/near directories to put wonderdraft files there.

Now open Wonderdraft, create new map with same dimensions as tile. Save it as tile name you are going to work on. Ie far/0_0. Now import this tile to the map. It will create land and sea depending on what is in tile. Update it with details like mountains, trees, ships, names. When done export it as webp with quality of no more than 85 to tiles/far/0_0.webp. 

You can see the progress by launching local web server (see above) and visiting http:/localhost:8000.

## Debugging

When running local web server visit dev.html.

It is instance that will highlight tile and show tile name in tooltip.


