// This file defines a C++ class AP and exposes it to Python using pybind11.
// The AP class has an integer ID and a greet method.
#include <pybind11/pybind11.h>
namespace py = pybind11;

// AP class definition
class AP
{
public:
  int ap_id; // Access Point ID

  // Constructor: initializes AP with a given ID
  explicit AP (int id) : ap_id (id) {}

  // Returns a greeting string containing the AP ID
  std::string
  greet () const
  {
    return "Hello from AP " + std::to_string (ap_id);
  }
};

// Python module definition using pybind11
PYBIND11_MODULE (ap, m)
{
  // Expose AP class to Python
  py::class_<AP> (m, "AP")
      .def (py::init<int> ())              // Constructor binding
      .def_readwrite ("ap_id", &AP::ap_id) // Expose ap_id for read/write
      .def ("greet", &AP::greet);          // Expose greet method
}
