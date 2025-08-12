#pragma once
#include <string>

class Node
{
public:
  int id;
  explicit Node (int id_ = -1);
  virtual ~Node () = default;
  [[nodiscard]] virtual std::string repr () const;
};
