import csv


def convert_to_gantt_csv(input_file, output_file):
    # Open input CSV file and read data into a dictionary
    with open(input_file, "r") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        data = [row for row in csv_reader]

    # Group data by date
    grouped_data = {}
    for row in data:
        date = row["DateTime"].split("-")[0:3]
        date_str = "_".join(date)
        if date_str not in grouped_data:
            grouped_data[date_str] = []
        grouped_data[date_str].append(row)

    # Write Gantt chart header
    with open(output_file, "w") as gantt_file:
        gantt_file.write("---\ndisplayMode: compact\n---\n\n")
        gantt_file.write("gantt\n")
        gantt_file.write("    title Daily Food Consumption\n")
        gantt_file.write("    dateFormat HH:mm\n")
        gantt_file.write("    axisFormat %H:%M\n\n")

        # Define Gantt chart sections
        gantt_file.write("    section Header\n")
        gantt_file.write("        Fasting window :00:00, 12:00\n")
        gantt_file.write("        Fasting window :20:00, 23:59\n")
        gantt_file.write("        Feeding window :12:00, 20:00\n\n")

        # Write Gantt chart data for each date
        for date, rows in grouped_data.items():
            gantt_file.write(f"    section {date}\n")
            for row in rows:
                time = row["DateTime"].split("-")[-1]
                food_item = row["FoodItem"]
                ftype = "active," if row["Type"].lower() == "liquid" else ""
                gantt_file.write(
                    f"        {food_item} :milestone, {ftype} {time}, 10m\n"
                )
            gantt_file.write("\n")


# Convert CSV data to Gantt chart format
convert_to_gantt_csv("food.csv", "food_consumption_gantt.txt")
