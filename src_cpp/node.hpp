#pragma once
#include <string>

class Node
{
public:
  static constexpr int INVALID_ID = -1;
  static constexpr int MAX_ID = 1000000;

  int id;
  explicit Node (int id_ = -1);
  virtual ~Node () = default;
  std::string repr () const;
};
