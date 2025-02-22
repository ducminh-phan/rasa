import os
from shutil import copyfile

import pytest

from rasa.core.test import CONFUSION_MATRIX_STORIES_FILE
from rasa.constants import RESULTS_FILE
from rasa.shared.constants import DEFAULT_RESULTS_PATH
from rasa.shared.utils.io import list_files, write_yaml
from typing import Callable
from _pytest.pytester import RunResult


def test_test_core(run_in_simple_project: Callable[..., RunResult]):
    run_in_simple_project("test", "core", "--stories", "data")

    assert os.path.exists("results")


def test_test_core_no_plot(run_in_simple_project: Callable[..., RunResult]):
    run_in_simple_project("test", "core", "--no-plot")

    assert not os.path.exists(f"results/{CONFUSION_MATRIX_STORIES_FILE}")


def test_test_core_with_no_model(run_in_simple_project: Callable[..., RunResult]):
    assert not os.path.exists("models")

    output = run_in_simple_project("test", "core")

    assert (
        "No model provided. Please make sure to specify the model to test with"
        in output.outlines[7]
    )


def test_test(run_in_simple_project_with_model: Callable[..., RunResult]):
    write_yaml(
        {
            "pipeline": "KeywordIntentClassifier",
            "policies": [{"name": "MemoizationPolicy"}],
        },
        "config2.yml",
    )

    run_in_simple_project_with_model("test")

    assert os.path.exists("results")
    assert os.path.exists("results/intent_histogram.png")
    assert os.path.exists("results/intent_confusion_matrix.png")


def test_test_with_no_user_utterance(
    run_in_simple_project_with_model: Callable[..., RunResult]
):
    write_yaml(
        {"pipeline": "KeywordIntentClassifier", "policies": [{"name": "TEDPolicy"}],},
        "config.yml",
    )

    simple_test_story_yaml = """
stories:
- story: happy path 1
  steps:
  - intent: greet
  - action: utter_greet
  - intent: mood_great
  - action: utter_happy
"""
    with open("tests/test_story_no_utterance.yaml", "w") as f:
        f.write(simple_test_story_yaml)

    run_in_simple_project_with_model("test", "--fail-on-prediction-errors")
    assert os.path.exists("results")
    assert not os.path.exists("results/failed_test_stories.yml")


def test_test_no_plot(run_in_simple_project: Callable[..., RunResult]):
    run_in_simple_project("test", "--no-plot")

    assert not os.path.exists("results/intent_histogram.png")
    assert not os.path.exists("results/intent_confusion_matrix.png")
    assert not os.path.exists("results/story_confmat.pdf")


def test_test_nlu(run_in_simple_project_with_model: Callable[..., RunResult]):
    run_in_simple_project_with_model("test", "nlu", "--nlu", "data", "--successes")

    assert os.path.exists("results/intent_histogram.png")
    assert os.path.exists("results/intent_confusion_matrix.png")
    assert os.path.exists("results/intent_successes.json")


def test_test_nlu_no_plot(run_in_simple_project: Callable[..., RunResult]):
    run_in_simple_project("test", "nlu", "--no-plot")

    assert not os.path.exists("results/intent_histogram.png")
    assert not os.path.exists("results/intent_confusion_matrix.png")


def test_test_nlu_cross_validation(run_in_simple_project: Callable[..., RunResult]):
    run_in_simple_project(
        "test", "nlu", "--cross-validation", "-c", "config.yml", "-f", "2", "-r", "1"
    )

    assert os.path.exists("results/intent_histogram.png")
    assert os.path.exists("results/intent_confusion_matrix.png")


def test_test_nlu_comparison(run_in_simple_project: Callable[..., RunResult]):
    write_yaml({"pipeline": "KeywordIntentClassifier"}, "config.yml")
    write_yaml({"pipeline": "KeywordIntentClassifier"}, "config2.yml")

    run_in_simple_project(
        "test",
        "nlu",
        "--config",
        "config.yml",
        "config2.yml",
        "--run",
        "2",
        "--percentages",
        "75",
        "25",
    )

    assert os.path.exists("results/run_1")
    assert os.path.exists("results/run_2")


def test_test_core_comparison(
    run_in_simple_project_with_model: Callable[..., RunResult]
):
    files = list_files("models")
    copyfile(files[0], "models/copy-model.tar.gz")

    run_in_simple_project_with_model(
        "test",
        "core",
        "-m",
        files[0],
        "models/copy-model.tar.gz",
        "--stories",
        "data/stories.md",
    )

    assert os.path.exists(os.path.join(DEFAULT_RESULTS_PATH, RESULTS_FILE))


def test_test_core_comparison_after_train(
    run_in_simple_project: Callable[..., RunResult]
):
    write_yaml(
        {"language": "en", "policies": [{"name": "MemoizationPolicy"}]}, "config_1.yml"
    )

    write_yaml(
        {"language": "en", "policies": [{"name": "MemoizationPolicy"}]}, "config_2.yml"
    )

    run_in_simple_project(
        "train",
        "core",
        "-c",
        "config_1.yml",
        "config_2.yml",
        "--stories",
        "data/stories.yml",
        "--runs",
        "2",
        "--percentages",
        "25",
        "75",
        "--out",
        "comparison_models",
    )

    assert os.path.exists("comparison_models")
    assert os.path.exists("comparison_models/run_1")
    assert os.path.exists("comparison_models/run_2")

    run_in_simple_project(
        "test",
        "core",
        "-m",
        "comparison_models",
        "--stories",
        "data/stories",
        "--evaluate-model-directory",
    )

    assert os.path.exists(os.path.join(DEFAULT_RESULTS_PATH, RESULTS_FILE))
    assert os.path.exists(
        os.path.join(DEFAULT_RESULTS_PATH, "core_model_comparison_graph.pdf")
    )


def test_test_help(run: Callable[..., RunResult]):
    output = run("test", "--help")

    help_text = """usage: rasa test [-h] [-v] [-vv] [--quiet] [-m MODEL] [-s STORIES]
                 [--max-stories MAX_STORIES] [--endpoints ENDPOINTS]
                 [--fail-on-prediction-errors] [--url URL]
                 [--evaluate-model-directory] [-u NLU]
                 [-c CONFIG [CONFIG ...]] [--cross-validation] [-f FOLDS]
                 [-r RUNS] [-p PERCENTAGES [PERCENTAGES ...]] [--no-plot]
                 [--successes] [--no-errors] [--out OUT]
                 {core,nlu} ..."""

    lines = help_text.split("\n")
    # expected help text lines should appear somewhere in the output
    printed_help = set(output.outlines)
    for line in lines:
        assert line in printed_help


def test_test_nlu_help(run: Callable[..., RunResult]):
    output = run("test", "nlu", "--help")

    help_text = """usage: rasa test nlu [-h] [-v] [-vv] [--quiet] [-m MODEL] [-u NLU] [--out OUT]
                     [-c CONFIG [CONFIG ...]] [--cross-validation] [-f FOLDS]
                     [-r RUNS] [-p PERCENTAGES [PERCENTAGES ...]] [--no-plot]
                     [--successes] [--no-errors]"""

    lines = help_text.split("\n")
    # expected help text lines should appear somewhere in the output
    printed_help = set(output.outlines)
    for line in lines:
        assert line in printed_help


def test_test_core_help(run: Callable[..., RunResult]):
    output = run("test", "core", "--help")

    help_text = """usage: rasa test core [-h] [-v] [-vv] [--quiet] [-m MODEL [MODEL ...]]
                      [-s STORIES] [--max-stories MAX_STORIES] [--out OUT]
                      [--e2e] [--endpoints ENDPOINTS]
                      [--fail-on-prediction-errors] [--url URL]
                      [--evaluate-model-directory] [--no-plot] [--successes]
                      [--no-errors]"""

    lines = help_text.split("\n")
    # expected help text lines should appear somewhere in the output
    printed_help = set(output.outlines)
    for line in lines:
        assert line in printed_help
