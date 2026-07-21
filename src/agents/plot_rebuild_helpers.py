{
  "imports": [
    { "name": "from typing import Any, Dict, List, Optional, TypeVar, Generic, Tuple", "location": "top" },
    { "name": "from datetime import datetime", "location": "top" },
    { "name": "from dataclasses import dataclass", "location": "top" }
  ],
  "types": [
    {
      "name": "RebuildResult",
      "body": "Rebuilder result tracking",
      "location": "after imports"
    }
  ],
  "helpers": [
    {
      "name": "_generate_arc_metadata",
      "body": "async def _generate_arc_metadata(): pass",
      "location": "in PlotAgent class"
    },
    {
      "name": "_archive_and_save_plots",
      "body": "async def _archive_and_save_plots(): pass",
      "location": "in PlotAgent class"
    }
  ]
}
