"""
Harness for the analyzer logic. It only tests the quality of its predictions.
It mocks all other parts of the system.

Assumptions
- performance is throughput (higher is better)

TODO
- initialize analyzerL
"""

__author__ = "Christos Kozyrakis"
__email__ = "christos@hyperpilot.io"
__copyright__ = "Copyright 2017, HyperPilot Inc"

from random import randint
import argparse
import json
import sys
from . import util
from . import bayesian_optimizer_pool

class CloudPerf(object):
  """ A class for a cloud performance model
  """

  def __init__(self,
               vcpu_a, vcpu_b, vcpu_c, vcpu_w,
               clk_a, clk_b, clk_c, clk_w,
               mem_a, mem_b, mem_c, mem_w,
               net_a, net_b, net_c, net_w,
               io_a, io_b, io_c, io_w,
               noise, nrange):
    """ initialize key parameters
    """
    self.vcpu_a = vcpu_a
    self.vcpu_b = vcpu_b
    self.vcpu_c = vcpu_c
    self.clk_a = clk_a
    self.clk_b = clk_b
    self.clk_c = clk_c
    self.mem_a = mem_a
    self.mem_b = mem_b
    self.mem_c = mem_c
    self.net_a = net_a
    self.net_b = net_b
    self.net_c = net_c
    self.io_a = io_a
    self.io_b = io_b
    self.io_c = io_c
    self.vcpu_w = vcpu_w,
    self.clk_w = clk_w,
    self.mem_w = mem_w,
    self.net_w = net_w,
    self.io_w = io_w,
    self.noise = noise
    self.nrange = nrange
    # some sanity checks
    if (vcpu_w + clk_w + mem_w + net_w + io_w) != 1.0:
      print("ERROR: Performance weights should sum to 1.0")
      sys.exit()
    if clk_a == 0 and clk_b == 0 and clk_c == 0 and clk_w != 0:
      print("ERROR: Clk performance parameters are all 0")
      sys.exit()
    if mem_a == 0 and mem_b == 0 and mem_c == 0 and mem_w != 0:
      print("ERROR: Mem performance parameters are all 0")
      sys.exit()
    if net_a == 0 and net_b == 0 and net_c == 0 and net_w != 0:
      print("ERROR: Net performance parameters are all 0")
      sys.exit()
    if io_a == 0 and io_b == 0 and io_c == 0 and io_w != 0:
      print("ERROR: IO performance parameters are all 0")
      sys.exit()


  def vcpu_model(self, vcpu):
    """ a vcpu based performance model.
        perf = vcpu / (a + vcpu*b + vcpu^2*b)
        interesting cases:  b=c=0, b>0/c=0, b>>0/c=0, b>>0/c>0
        assumes vcpu_min = 1
    """
    return vcpu / (self.vcpu_a + self.vcpu_b*vcpu + self.vcpu_c*vcpu*vcpu)

  def clk_model(self, clk):
    """ a clk based performance model.
        perf = clk / (a + clk*b + clk^2*b)
        assumes clk_min = 2.3
    """
    clk = (clk / 2.3)
    return clk / (self.clk_a + self.clk_b*clk + self.clk_c*clk*clk)

  def mem_model(self, mem):
    """ a mem based performance model.
        perf = mem / (a + mem*b + mem^2*b)
        interesting cases:  b=c=0, b>0/c=0, b>>0/c=0, b>>0/c>0
        assumes mem_min = 0.5
    """
    mem = (mem / 0.5)
    return mem / (self.mem_a + self.mem_b*mem + self.mem_c*mem*mem)

  def net_model(self, net):
    """ a net based performance model.
        perf = net / (a + net*b + net^2*b)
        interesting cases:  b=c=0, b>0/c=0, b>>0/c=0, b>>0/c>0
        assumes net_min = 100
    """
    net = (net / 100)
    return net / (self.net_a + self.net_b*net + self.net_c*net*net)

  def io_model(self, io):
    """ a io based performance model.
        perf = io / (a + io*b + io^2*b)
        interesting cases:  b=c=0, b>0/c=0, b>>0/c=0, b>>0/c>0
        assumes io_min = 50
    """
    io = (io / 50)
    return io / (self.io_a + self.io_b*io + self.io_c*io*io)

  def perf(self, vcpu, clk, mem, net, io, noise):
    """ estimate performance
    """
    perf = self.vcpu_w * self.vcpu_model(vcpu) + \
           self.clk_w * self.clk_model(clk) + \
           self.mem_w * self.mem_model(mem) + \
           self.net_w * self.net_model(net) + \
           self.io_w * self.io_model(io)
    if noise and self.noise:
      change = randint((-1) * self.nrange, self.nrange)
      perf += perf*change/100
    return perf


def __main__():
  """ Main function of analyzer harness
  """

  # parse arguments
  parser = argparse.ArgumentParser()
  parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
  parser.add_argument("-i", "--iter", type=int, required=False, default=10,
                      help="maximum iterations")
  parser.add_argument("-n", "--noise", help="add noise to cloud performance", action="store_false")
  parser.add_argument("-r", "--nrange", type=int, required=False, default=10,
                      help="noise range (int)")
  parser.add_argument("-va", "-vcpua", type=float, required=False, default=1.0, help="vcpu a")
  parser.add_argument("-vb", "-vcpub", type=float, required=False, default=0.0, help="vcpu b")
  parser.add_argument("-vc", "-vcpuc", type=float, required=False, default=0.0, help="vcpu c")
  parser.add_argument("-vw", "-vcpuw", type=float, required=False, default=0.2, help="vcpu w")
  parser.add_argument("-ca", "-clka", type=float, required=False, default=1.0, help="clk a")
  parser.add_argument("-cb", "-clkb", type=float, required=False, default=0.0, help="clk b")
  parser.add_argument("-cc", "-clkc", type=float, required=False, default=0.0, help="clk c")
  parser.add_argument("-cw", "-clkw", type=float, required=False, default=0.2, help="clk w")
  parser.add_argument("-ma", "-mema", type=float, required=False, default=1.0, help="mem a")
  parser.add_argument("-mb", "-memb", type=float, required=False, default=0.0, help="mem b")
  parser.add_argument("-mc", "-memc", type=float, required=False, default=0.0, help="mem c")
  parser.add_argument("-mw", "-memw", type=float, required=False, default=0.2, help="mem w")
  parser.add_argument("-na", "-neta", type=float, required=False, default=1.0, help="net a")
  parser.add_argument("-nb", "-netb", type=float, required=False, default=0.0, help="net b")
  parser.add_argument("-nc", "-netc", type=float, required=False, default=0.0, help="net c")
  parser.add_argument("-nw", "-netw", type=float, required=False, default=0.2, help="net w")
  parser.add_argument("-ia", "-ioa", type=float, required=False, default=1.0, help="io a")
  parser.add_argument("-ib", "-iob", type=float, required=False, default=0.0, help="io b")
  parser.add_argument("-ic", "-ioc", type=float, required=False, default=0.0, help="io c")
  parser.add_argument("-iw", "-iow", type=float, required=False, default=0.2, help="io w")
  args = parser.parse_args()

  # initialize performance model
  cloud_perf = CloudPerf(args.vcpua, args.vcpub, args.vcpc, args.vcpuw, \
                         args.clka, args.clkb, args.clkc, args.clkw, \
                         args.mema, args.memb, args.memc, args.memw, \
                         args.neta, args.netb, args.netc, args.netw, \
                         args.ioa, args.iob, args.ioc, args.iow, \
                         args.noise, args.nrange)

  # initialyze analyzer
  # TODO

  # get all the instance info
  all_nodetypes = util.get_all_nodetypes()
  numtypes = len(all_nodetypes)
  if numtypes < args.iter*3:
    print("ERROR: Not enough nodetypes in database")
    sys.exit()
  # build dictionary with features for all instances
  features = {}
  for nodetype in all_nodetypes:
    feat = util.encode_instance_type(nodetype)
    features[nodetype] = feat
  # visited instances
  visited = set()

  # provide 3 random instances to analyzer
  rand = randint(0, numtypes)
  type1 = features.keys()[rand]
  feat = features[type1]
  perf1 = cloud_perf.perf(feat[0], feat[1], feat[2], feat[3], feat[4], True)
  visited.add(type1)
  rand = randint(0, numtypes)
  type2 = features.keys()[rand]
  feat = features[type2]
  perf2 = cloud_perf.perf(feat[0], feat[1], feat[2], feat[3], feat[4], True)
  visited.add(type2)
  type3 = features.keys()[rand]
  feat = features[type3]
  feat = util.encode_instance_type(type3)
  perf3 = cloud_perf.perf(feat[0], feat[1], feat[2], feat[3], feat[4], True)
  visited.add(type3)
  request_str = "{\"appName\": \"redis\", \
                 \"data\": [ {\"instanceType\": \"%s\", \"qosValue\": %f}, \
                             {\"instanceType\": \"%s\", \"qosValue\": %f}, \
                             {\"instanceType\": \"%s\", \"qosValue\": %f}]}" \
                 %(type1, perf1, type2, perf2, type3, perf3)
  request_dict = json.loads(request_str)
  analyzer.get_candidates("redis", request_dict)

  #main loop
  for i in range(args.iters):
    # check if done
    while True:
      status_str = analyzer.get_status("redis")
      status_dict = json.loads(status_str)
      if status_dict["Status"] != "Running":
        break
    # throw error if needed
    if status_dict["Status"] != "Done":
      print("ERROR: Analyzer returned with status %s"  %status_dict["Status"])
      sys.exit()
    # termination
    if len(status_dict["instance_type"]) == 0:
      break
    # prepare next candidates
    request_str = "{\"appName\": \"redis\", \"data\": [ "
    count = 0
    for nodetype in status_dict["instance_type"]:
      count += 1
      feat = features[nodetype]
      perf = cloud_perf.perf(feat[0], feat[1], feat[2], feat[3], feat[4], True)
      request_str += "{\"instanceType\": \"%s\", \"qosValue\": %f}" %(nodetype, perf)
      if count < len(status_dict["instance_type"]):
        request_str += ", "
      if nodetype in visited:
        print("WARNING: reconsidering type %s" %nodetype)
      else:
        visited.add(nodetype)
    request_str += "]}"
    request_dict = json.loads(request_str)
    analyzer.get_candidates("redis", request_dict)

  # evaluate results
  slo = util.get_slo_value("redis")
  budget = util.get_budget_value("redis")
  # scan all visited nodetypes
  visited_perfcost_i = visited_perf_i = visited_cost_i = "none"
  visited_perfcost = visited_perf = visited_cost = -1.0
  for key in visited:
    feat = features[key]
    perf = cloud_perf.perf(feat[0], feat[1], feat[2], feat[3], feat[4], False)
    price = util.get_price(key)
    cost = util.compute_cost(price, 'throughput', perf)
    if perf > visited_perf and cost <= budget:
      visited_perf_i = key
      visited_perf = perf
    if cost < visited_cost and perf >= slo:
      visited_cost_i = key
      visited_cost = cost
    if (perf/cost) > visited_perfcost:
      visited_perfcost_i = key
      visited_perfcost = perf/cost
  # scan all nodetypes
  cloud_perfcost_i = cloud_perf_i = cloud_cost_i = "none"
  cloud_perfcost = cloud_perf = cloud_cost = -1.0
  for key in features:
    feat = features[key]
    perf = cloud_perf.perf(feat[0], feat[1], feat[2], feat[3], feat[4], False)
    price = util.get_price(key)
    cost = util.compute_cost(price, 'throughput', perf)
    if perf > cloud_perf and cost <= budget:
      cloud_perf_i = key
      cloud_perf = perf
    if cost < cloud_cost and perf >= slo:
      cloud_cost_i = key
      cloud_cost = cost
    if (perf/cost) > cloud_perfcost:
      cloud_perfcost_i = key
      cloud_perfcost = perf/cost

  # print results
  print("")
  print("")
  print(".......................")
  print("... Analyzer results...")
  print("Iterations (requested/done): %d/%d", args.iter, i)
  print("Noise: ", args.noise)
  print("Noise range: ", args.nrange)
  print("Min perf: ", slo)
  print("Max cost: ", budget)
  print("")
  print("Performance/cost")
  print("   Best avalailable: %s, performance/cost %f" %(cloud_perfcost_i, cloud_perfcost))
  print("   Best found: %s, performance/cost %f" %(visited_perfcost_i, visited_perfcost))
  print("Perfomance with cost constraint")
  print("   Best avalailable: %s, performance %f" %(cloud_perf_i, cloud_perf))
  print("   Best found: %s, performance %f" %(visited_perf_i, visited_perf))
  print("Cost with performance constraint")
  print("   Best avalailable: %s, cost %f" %(cloud_cost_i, cloud_cost))
  print("   Best found: %s, cost %f" %(visited_cost_i, cloud_cost))

__main__()
