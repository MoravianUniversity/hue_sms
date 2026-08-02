from setuptools import find_packages, setup

setup(
    name="hue_sms",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={
        "hue_sms": [
            "data/*.csv",
            "web/templates/*.html",
            "generate_colors/wikipedia_pages/*.html",
        ],
    },
    include_package_data=True,
)
