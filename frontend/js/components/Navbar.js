import React, { Component } from "react";
import Drawer from "material-ui/Drawer";
import AppBar from "material-ui/AppBar";
import { List, ListItem, makeSelectable } from "material-ui/List";
import _ from "lodash";

const SelectableList = makeSelectable(List);

export default ({ availableApps, selectedItem, selectItem }) => (
  <Drawer open>
    <AppBar title="Analyzer" />
    <SelectableList value={selectedItem} onChange={selectItem}>
      {_.map(availableApps, (apps, category) => (
        <ListItem
          key={category}
          primaryText={_.capitalize(category)}
          primaryTogglesNestedList={true}
          initiallyOpen={true}
          nestedItems={apps.map(({ _id, appName }) => (
            <ListItem
              primaryText={appName}
              secondaryText={_id}
              value={`/${category}/${_id}`}
              key={_id} />
          ))}
        />
      ))}
    </SelectableList>
  </Drawer>
)
