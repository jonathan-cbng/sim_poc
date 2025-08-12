#pragma once
#include "node.hpp"
#include "rt.hpp"
#include <memory>
#include <set>
#include <string>

class AP : public Node, public std::enable_shared_from_this<AP>
{
public:
  std::set<std::shared_ptr<RT> > rts;

  explicit AP (int id = INVALID_ID);

  void add_rt (const std::shared_ptr<RT> &rt);
  void remove_rt (const std::shared_ptr<RT> &rt);
  std::string repr () const;
};
