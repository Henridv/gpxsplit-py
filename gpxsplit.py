#!/usr/bin/python

#######
# Script to convert .gpx-tracks into routes with a limited number of points
# Some Garmin GPS (e.g., GPSmap 62s) can't handle routes longer than 250 points
# Takes 1-n input gpx-file(s) and converts them into 1-m output gpx-files (see also help (-h) and readme.md)
# requires gpxpy
#######

import os
import sys
import argparse
import math

import gpxpy.gpx
import gpxpy.geo

import logging

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger("gpxsplit")

parser = argparse.ArgumentParser()
parser.add_argument(
    "-i",
    "--input",
    help="Input file(s)",
    type=argparse.FileType("r"),
    nargs="+",
    required=True,
)

DEFAULT_OUTPUTNAME = "output.gpx"
parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Output filename. If --splitfiles is given, <filename>_route_split{i}.gpx is used",
)
parser.add_argument(
    "-s",
    "--simplify",
    action="store_true",
    help="If set, the path is simplified with gpxpy and --min_distance",
)
parser.add_argument(
    "--output_dir",
    default="./",
    type=str,
    help="Defines the output directory. Is created if it doesn't exist",
)
parser.add_argument(
    "--splitfiles",
    action="store_true",
    help="If set, each track is saved in a separate file with pattern {i}_<output filename>",
)
parser.add_argument(
    "--max_distance",
    type=float,
    default=5,
    help="Minimum distance two points need to have for being kept separate",
)
parser.add_argument(
    "--max_route_length",
    type=int,
    default=250,
    help="The maximum length of a single route. The whole point of this thing. Important since some "
    "GPS devices can't handle routes longer than 250 points",
)

args = parser.parse_args()

os.makedirs(os.path.dirname(args.output_dir), exist_ok=True)

# Define how the output file should be named. If there
if args.output is None:
    if len(args.input) == 1:
        # If no output filename is given and we have exactly one input file, take this as the base
        args.output = os.path.splitext(os.path.basename(args.input[0].name))[0]
        logger.debug(f"Setting output file to {args.output}")
    else:
        # If no output filename is given but also more than one file is used as input, use DEFAULT_OUTPUTNAME
        args.output = os.path.splitext(DEFAULT_OUTPUTNAME)[0]
        logger.debug(f"Setting output file to {args.output}")

else:
    # Take what is given as output file. (Still prepends/appends indices/info about the splitting
    args.output = os.path.splitext(args.output)[0]
    logger.debug(f"Setting output file to {args.output}")

logger.info(f"Found {len(args.input)} input files")
if args.simplify:
    logger.info(f"Simplication is on with a maximum distance of {args.max_distance}m")
else:
    logger.info("Simplification is off")

routes_new = []

for gpxfile in args.input:
    logger.debug(f"Parsing {gpxfile}")
    gpx = gpxpy.parse(gpxfile)

    if args.simplify:
        gpxlen_before = gpx.get_points_no()
        gpx.simplify(max_distance=args.max_distance)
        gpxlen_after = gpx.get_points_no()
        logger.debug(f"Simplified track from {gpxlen_before} to {gpxlen_after} points")

    route_idx = 0
    for track_idx, track in enumerate(gpx.tracks):
        point_idx = 0
        for segment_idx, segment in enumerate(track.segments):
            # Creates a list of lists of points (sublists of segment) with at most max_route_length points
            # As many as necessary to cover the entire segment
            subsegments = [
                segment.points[start : start + args.max_route_length]
                for start in range(0, len(segment.points), args.max_route_length)
            ]
            logger.debug(f"Split segment into {len(subsegments)} subsegments")

            # For each subsegment we create a separate route
            for sublist_idx, sublist in enumerate(subsegments):
                # routename = f"t{track_idx:01}s{segment_idx:01}r{sublist_idx}_{os.path.basename(gpxfile.name)}"
                routename = f"{route_idx:03}_{os.path.splitext(os.path.basename(gpxfile.name))[0]}"
                logger.debug(f"Creating route {routename}")

                for point in sublist:
                    point_idx += 1
                    if point.name is None:
                        point.name = f"{point_idx:0{math.ceil(math.log10(args.max_route_length))}}"

                route_new = gpxpy.gpx.GPXRoute(name=routename)
                route_new.points = sublist
                routes_new.append(route_new)
                route_idx += 1

    logger.info(
        f"Created {route_idx} routes of maximum length {args.max_route_length} for file {gpxfile.name}"
    )

if args.splitfiles:
    # Create a file for each track
    for route_new_idx, route_new in enumerate(routes_new):
        gpx_new = gpxpy.gpx.GPX()
        gpx_new.routes.append(route_new)
        filename = (
            f"{route_new_idx}_{args.output}_route_split{args.max_route_length}.gpx"
        )
        with open(os.path.join(args.output_dir, filename), "w") as fp:
            logger.debug(f"Writing {filename}")
            fp.write(gpx_new.to_xml())
    logger.info(f"Wrote {len(routes_new)} files")
else:
    # Create one file for all tracks
    gpx_new = gpxpy.gpx.GPX()
    gpx_new.routes.extend(routes_new)
    filename = f"{args.output}_route_split{args.max_route_length}.gpx"
    with open(os.path.join(args.output_dir, filename), "w") as fp:
        logger.debug(f"Writing {filename}")
        fp.write(gpx_new.to_xml())
