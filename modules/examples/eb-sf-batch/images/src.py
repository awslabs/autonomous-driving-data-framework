import pandas as pd

# initialize list of lists
data = [["Cristiano Ronlado", 1], ["Juan Mata", 2], ["Bruno Fernandez", 3]]

# Create the pandas DataFrame
df = pd.DataFrame(data, columns=["Name", "Jersey Number"])

print("-" * 50)
print("StepFunctions - eventbridge - AWS Batch workflow tested")
print("-" * 50)
print(df)
print("-" * 50)
