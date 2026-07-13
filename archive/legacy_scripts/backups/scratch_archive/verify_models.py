import os
import sys

sys.path.append(os.getcwd())


from models import WorldBible, WorldBibleCore


def test_model():
    bible = WorldBible()
    print(f"WorldBible absolute_dictionary: {bible.absolute_dictionary}")

    core = WorldBibleCore()
    print(f"WorldBibleCore absolute_dictionary: {core.absolute_dictionary}")

    core.absolute_dictionary = {"Protagonist": "Alvin"}
    print(f"Updated absolute_dictionary: {core.absolute_dictionary}")

if __name__ == "__main__":
    test_model()

