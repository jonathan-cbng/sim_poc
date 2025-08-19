#include "ap.hpp"
#include "node.hpp"
#include "rt.hpp"
#include <memory>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

PYBIND11_MODULE (_node_sim, m)
{
  py::class_<Node, std::shared_ptr<Node> > (m, "_Node")
      .def (py::init<int> (), py::arg ("id") = Node::INVALID_ID)
      .def_readwrite ("id", &Node::id)
      .def ("__repr__", &Node::repr);

  py::class_<AP, Node, std::shared_ptr<AP> > (m, "_AP")
      .def (py::init<int> (), py::arg ("id") = AP::INVALID_ID)
      .def ("add_rt", &AP::add_rt)
      .def ("remove_rt", &AP::remove_rt)
      .def_readwrite ("rts", &AP::rts)
      .def ("__repr__", &AP::repr);

  py::class_<RT, Node, std::shared_ptr<RT> > (m, "_RT")
      .def (py::init<int> (), py::arg ("id") = RT::INVALID_ID)
      .def_readwrite ("ap", &RT::ap)
      .def ("__repr__", &RT::repr);
}
